"""Каскадная логика доставки уведомлений (без Celery/Redis — поллинг DB-воркером).

Каскад по ТЗ: Web Push (1) → Telegram (2) → SMS (3) → e-mail (4), с эскалацией по таймерам,
если сотрудник не прошёл опрос. Дедуп, дневной лимит, DND, 152-ФЗ, рабочие часы для SMS.
"""
import logging
import os
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from apps.accounts.models import Employee
from apps.surveys.models import Participation, Survey

from .channels import email as email_ch
from .channels import sms as sms_ch
from .channels import telegram as tg_ch
from .channels import webpush as push_ch
from .models import ChannelPrefs, NotificationJob, NotificationLog

log = logging.getLogger("notifications")

# Стадии каскада: (имя, поле-настройка, адаптер). Поле-настройка отражает тумблер канала.
STAGES = [
    ("push", "web_push", push_ch.send),
    ("telegram", "telegram", tg_ch.send),
    ("sms", "sms", sms_ch.send),
    ("email", "email", email_ch.send),
]
ORDER = [s[0] for s in STAGES]

# Таймеры эскалации по ТЗ (через сколько пробовать СЛЕДУЮЩИЙ канал, если не прошёл).
STAGE_DELAY = {"push": timedelta(hours=4), "telegram": timedelta(hours=8),
               "sms": timedelta(days=7), "email": timedelta(0)}

DAILY_CAP = 5  # не более 5 уведомлений в сутки на сотрудника (антиспам)


def _demo_seconds():
    """Демо-режим: NOTIF_DEMO_SECONDS схлопывает таймеры эскалации до N секунд."""
    raw = os.environ.get("NOTIF_DEMO_SECONDS")
    return int(raw) if raw and raw.isdigit() else None


def _delay_for(stage):
    demo = _demo_seconds()
    return timedelta(seconds=demo) if demo is not None else STAGE_DELAY[stage]


def _payload(survey):
    minutes = max(1, survey.questions.count())
    ends = survey.ends_at.strftime("%d.%m") if survey.ends_at else "—"
    return {
        "title": f"Новый опрос: {survey.title}",
        "body": f"До окончания — {ends}. Время прохождения — ~{minutes} мин.",
        "url": f"{settings.PUBLIC_BASE_URL}/s/{survey.id}",
        "survey_id": survey.id,
        "survey_title": survey.title,
    }


def _audience(survey):
    qs = Employee.objects.filter(role=Employee.EMPLOYEE)
    if survey.audience_departments:
        qs = qs.filter(department__in=survey.audience_departments)
    return qs


# ---------------------------------------------------------------- enqueue (триггеры)

def enqueue_for_trigger(survey, trigger):
    """Поставить каскадные задания аудитории (исключая прошедших и без согласия)."""
    taken = set(Participation.objects.filter(survey=survey).values_list("employee_id", flat=True))
    now = timezone.now()
    created = 0
    for emp in _audience(survey):
        if emp.id in taken:
            continue
        if not survey.critical and not emp.consent_active:
            continue  # 152-ФЗ: без согласия не шлём (кроме критичных)
        _, was_created = NotificationJob.objects.get_or_create(
            dedup_key=f"{survey.id}:{emp.id}:{trigger}",
            defaults={"survey": survey, "employee": emp, "trigger": trigger,
                      "stage": NotificationJob.PUSH, "next_attempt_at": now,
                      "critical": survey.critical},
        )
        created += was_created
    log.info("enqueue %s/%s: +%d заданий", survey.id, trigger, created)
    return created


# ---------------------------------------------------------------- scheduler (напоминания)

_last_purge = None


def run_scheduler(now=None):
    """Напоминания 48ч/24ч + авто-чистка мягко-удалённых опросов старше 30 дней."""
    now = now or timezone.now()
    for survey in Survey.objects.filter(status=Survey.ACTIVE, ends_at__isnull=False,
                                        deleted_at__isnull=True):
        hours_left = (survey.ends_at - now).total_seconds() / 3600
        if 24 < hours_left <= 48:
            enqueue_for_trigger(survey, "reminder48")
        elif 0 < hours_left <= 24:
            enqueue_for_trigger(survey, "reminder24")

    global _last_purge
    if _last_purge is None or (now - _last_purge).total_seconds() > 3600:
        Survey.objects.filter(deleted_at__lt=now - timedelta(days=30)).delete()
        _last_purge = now


# ---------------------------------------------------------------- dispatch (каскад)

def _sent_today(employee, now):
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return NotificationLog.objects.filter(
        employee=employee, created_at__gte=start,
        status__in=[NotificationLog.SENT, NotificationLog.DELIVERED],
    ).count()


def _within_sms_hours(now):
    if os.environ.get("NOTIF_SMS_ANYTIME", "1") == "1":
        return True
    return 9 <= timezone.localtime(now).hour < 18


def _already_sent(survey, employee, channel):
    # Dedup только для платных каналов (SMS/email) — push и tg можно слать повторно
    if channel not in ("sms", "email"):
        return False
    return NotificationLog.objects.filter(
        survey=survey, employee=employee, channel=channel, status=NotificationLog.SENT,
    ).exists()


def process_job(job, now):
    emp = job.employee
    survey = job.survey

    if Participation.objects.filter(survey=survey, employee=emp).exists():
        job.status = NotificationJob.COMPLETED
        job.save(update_fields=["status"])
        return
    if not job.critical and not emp.consent_active:
        job.status = NotificationJob.STOPPED
        job.save(update_fields=["status"])
        return

    prefs, _ = ChannelPrefs.objects.get_or_create(employee=emp)
    if not job.critical and prefs.dnd_until and prefs.dnd_until > now:
        job.next_attempt_at = prefs.dnd_until
        job.save(update_fields=["next_attempt_at"])
        return
    if not job.critical and _demo_seconds() is None and _sent_today(emp, now) >= DAILY_CAP:
        job.next_attempt_at = now + timedelta(hours=1)
        job.save(update_fields=["next_attempt_at"])
        return

    payload = _payload(survey)
    idx = ORDER.index(job.stage) if job.stage in ORDER else len(ORDER)
    for i in range(idx, len(STAGES)):
        channel, pref_attr, sender = STAGES[i]
        # тумблер канала (критичные доставляются независимо от настроек)
        if not job.critical and not prefs.channel_enabled(pref_attr):
            continue
        if channel == "sms" and not _within_sms_hours(now):
            job.next_attempt_at = now + timedelta(hours=1)
            job.save(update_fields=["next_attempt_at"])
            return
        if _already_sent(survey, emp, channel):
            continue  # дедуп: этот канал по этому опросу уже отработал

        res = sender(emp, payload)
        NotificationLog.objects.create(
            employee=emp, survey=survey, channel=channel,
            status=NotificationLog.SENT if res.ok else NotificationLog.FAILED,
            cost=res.cost, detail=res.detail,
            dedup_key=f"{survey.id}:{emp.id}:{channel}",
        )
        job.attempt += 1
        if res.ok:
            # успех → ждём таймер, затем эскалация к следующему каналу, если не прошёл
            nxt = i + 1
            if nxt >= len(ORDER):
                job.stage = NotificationJob.DONE
                job.status = NotificationJob.COMPLETED
            else:
                job.stage = ORDER[nxt]
                job.next_attempt_at = now + _delay_for(channel)
            job.save(update_fields=["stage", "status", "next_attempt_at", "attempt"])
            return
        # неуспех (нет подписки/не привязан) → сразу пробуем следующий канал
    # каналы исчерпаны
    job.stage = NotificationJob.DONE
    job.status = NotificationJob.COMPLETED
    job.save(update_fields=["stage", "status", "attempt"])


def dispatch_due(now=None, batch=200):
    now = now or timezone.now()
    jobs = NotificationJob.objects.filter(
        status=NotificationJob.ACTIVE, next_attempt_at__lte=now,
    ).select_related("employee", "survey")[:batch]
    for job in jobs:
        try:
            process_job(job, now)
        except Exception as e:  # noqa: BLE001
            log.warning("process_job %s fail: %s", job.id, e)
