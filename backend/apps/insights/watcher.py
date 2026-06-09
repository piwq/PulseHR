"""Авто-петля инсайтов (closed-loop): детектор просадки отделов.

Замыкает «вау-петлю» в автономную: метрика отдела просела → создаём Insight →
готовая проводка сама доставляет алерт (бот поллит Insight severity>=2 → Telegram;
SSE-стрим → тост на дашборде HR). Здесь только ДЕТЕКЦИЯ — доставку не дублируем.

Включается флагом INSIGHTS_AUTO=1 (по умолчанию выкл — чтобы на демо HR мог
контролировать момент ручной кнопкой analyze). Кулдаун защищает от дублей.
"""
import os
from datetime import timedelta

from django.utils import timezone

from apps.surveys import analytics
from apps.surveys.models import SurveyRun

from .llm import analyze_texts
from .models import Insight

SEV_NUM = {"medium": 2, "critical": 3}  # severity_for → Insight.severity (бот/SSE: >=2)
DEFAULT_COOLDOWN = 21600  # 6 часов


def _enabled():
    return os.environ.get("INSIGHTS_AUTO", "0") == "1"


def _cooldown():
    """Окно дедупа: один алерт на (опрос, отдел, severity) в это окно. Default 6ч.

    Независимо от NOTIF_DEMO_SECONDS — иначе на демо алерт бы пересоздавался каждые
    несколько секунд. Для повторного прогона на демо просто понизить INSIGHTS_COOLDOWN.
    """
    raw = os.environ.get("INSIGHTS_COOLDOWN", str(DEFAULT_COOLDOWN))
    return timedelta(seconds=int(raw) if raw.isdigit() else DEFAULT_COOLDOWN)


def run_watcher(now=None):
    """Создать Insight по проблемным отделам активных опросов. Возвращает число созданных."""
    if not _enabled():
        return 0
    now = now or timezone.now()
    cooldown = _cooldown()
    created = 0
    for run in SurveyRun.objects.filter(status=SurveyRun.ACTIVE,
                                        survey__deleted_at__isnull=True).select_related("survey"):
        if not run.responses.exists():
            continue
        for d in analytics.department_breakdown(run):
            if d.get("suppressed"):
                continue
            sev = SEV_NUM.get(d.get("sev"))
            if not sev:
                continue
            dept = d["department"]
            # Кулдаун: не плодим дубль того же (волна, отдел) с severity >= текущего.
            if Insight.objects.filter(run=run, department=dept, severity__gte=sev,
                                      created_at__gte=now - cooldown).exists():
                continue
            rs = list(analytics.filtered_responses(run, department=dept))
            cause = analyze_texts(analytics.comments(run, responses=rs)).get("summary", "")
            summary = (f"Отдел «{dept}»: индекс вовлечённости {d.get('eng')}. "
                       f"{d.get('note')}. Причина (AI): {cause}")
            Insight.objects.create(run=run, survey=run.survey, department=dept,
                                   summary=summary, severity=sev)
            created += 1
    return created
