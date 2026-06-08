"""Демо-данные под новые модели (РАБОЧЕЕ).

Создаёт:
- HR-аккаунт + сотрудников по отделам (для OTP-входа и % прохождения);
- активный анонимный опрос с вопросами scale / NPS / single / text;
- backdated анонимные ответы 3 волнами с падающим трендом «Продаж» (драматургия демо);
- участия (Participation) части сотрудников для реального % прохождения.

Запуск: docker compose exec core python scripts/seed.py
"""
import os
import random
import sys
from datetime import timedelta

import django

# scripts/ запускается напрямую — добавим backend/ (родитель) в path для импорта config.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.utils import timezone  # noqa: E402

from apps.accounts.models import Employee  # noqa: E402
from apps.surveys.models import (Answer, Participation, Question,  # noqa: E402
                                 Response, Survey)

DEPTS = ["Продажи", "Разработка", "Поддержка", "Маркетинг", "HR"]
WAVES = 3
WAVE_GAP_DAYS = 14
RESP_PER_WAVE = 8           # >= гейта анонимности N>=5
EMP_PER_DEPT = 8

# Падающая вовлечённость у «Продаж» по волнам (1–5).
ENG = {
    "Продажи":    [4.3, 3.4, 2.6],
    "Разработка": [4.1, 4.0, 4.2],
    "Поддержка":  [3.8, 3.9, 3.7],
    "Маркетинг":  [3.9, 3.8, 3.9],
    "HR":         [4.0, 4.0, 4.1],
}
CHOICES = ["Переработки", "Зарплата", "Руководство", "Процессы", "Ничего"]
NEG = ["Постоянные переработки, не успеваю восстановиться.", "Горят сроки, слишком много задач.",
       "Не хватает обратной связи от руководителя.", "Выгораю, думаю о смене работы."]
POS = ["В целом нормально, команда поддерживает.", "Нравятся задачи, но нагрузка высокая."]


def run():
    # --- аккаунты ---
    Employee.objects.get_or_create(
        phone="+79990000000",
        defaults={"name": "Анна Котова", "role": Employee.HR, "department": "HR"},
    )
    employees = {d: [] for d in DEPTS}
    for di, dept in enumerate(DEPTS):
        for i in range(EMP_PER_DEPT):
            emp, _ = Employee.objects.get_or_create(
                phone=f"+7900{di}{i:03d}",
                defaults={"name": f"{dept} {i+1}", "role": Employee.EMPLOYEE,
                          "department": dept, "consent_at": timezone.now()},
            )
            employees[dept].append(emp)

    # --- опрос ---
    Survey.objects.filter(title="Пульс-опрос Q2").delete()
    survey = Survey.objects.create(
        title="Пульс-опрос Q2", description="Демо-опрос вовлечённости.",
        mode=Survey.ANONYMOUS, status=Survey.ACTIVE, is_active=True,
        starts_at=timezone.now() - timedelta(days=45),
        ends_at=timezone.now() + timedelta(days=10),
    )
    q_eng = Question.objects.create(survey=survey, order=1, qtype=Question.SCALE,
        text="Оцените вовлечённость", config={"min": 1, "max": 5, "low": "Низкая", "high": "Высокая"})
    q_nps = Question.objects.create(survey=survey, order=2, qtype=Question.SCALE,
        text="Порекомендуете компанию как место работы?", config={"min": 0, "max": 10, "nps": True})
    q_choice = Question.objects.create(survey=survey, order=3, qtype=Question.SINGLE,
        text="Что больше всего мешает в работе?", config={"options": CHOICES})
    q_text = Question.objects.create(survey=survey, order=4, qtype=Question.TEXT,
        text="Что бы вы изменили?", required=False)

    # --- backdated анонимные ответы (для тренда/eNPS/распределения) ---
    now = timezone.now()
    for wave in range(WAVES):
        wave_dt = now - timedelta(days=WAVE_GAP_DAYS * (WAVES - wave))
        for dept in DEPTS:
            eng_mean = ENG[dept][wave]
            for _ in range(RESP_PER_WAVE):
                r = Response.objects.create(survey=survey, department=dept, session_id="seed")
                Response.objects.filter(pk=r.pk).update(submitted_at=wave_dt)
                eng = max(1, min(5, round(random.gauss(eng_mean, 0.5))))
                nps = max(0, min(10, round(random.gauss(eng_mean * 2, 1.5))))
                Answer.objects.create(response=r, question=q_eng, value_num=eng)
                Answer.objects.create(response=r, question=q_nps, value_num=nps)
                weights = [5, 2, 2, 1, 1] if dept == "Продажи" and eng <= 3 else [1, 2, 1, 2, 4]
                Answer.objects.create(response=r, question=q_choice,
                                      value_json=random.choices(CHOICES, weights=weights)[0])
                Answer.objects.create(response=r, question=q_text,
                                      value_text=random.choice(NEG if eng <= 3 else POS))

    # --- участия (для % прохождения): ~70% сотрудников ---
    for dept in DEPTS:
        for emp in employees[dept]:
            if random.random() < 0.7:
                Participation.objects.get_or_create(survey=survey, employee=emp)

    print(f"Seed готов: survey #{survey.id}, {WAVES} волн × {len(DEPTS)} отделов, "
          f"{Employee.objects.count()} аккаунтов.")


if __name__ == "__main__":
    run()
