"""Демо-данные под модель волн (SurveyRun).

Создаёт:
- HR-аккаунт + сотрудников по отделам (для OTP-входа и % прохождения);
- один анонимный опрос вовлечённости с вопросами scale / NPS / single / text;
- НЕСКОЛЬКО ВОЛН (запусков) с падающим трендом «Продаж» от волны к волне —
  для сравнения во времени и дельты «к прошлой волне» (последняя волна — активная);
- участия (Participation) per-run для реального % прохождения.

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
                                 Response, Survey, SurveyRun)

DEPTS = ["Продажи", "Разработка", "Поддержка", "Маркетинг", "HR"]
CITIES = ["Москва", "Санкт-Петербург", "Казань"]
TITLES = {
    "Продажи":    ["Менеджер по продажам", "Старший менеджер"],
    "Разработка": ["Разработчик", "Тимлид"],
    "Поддержка":  ["Специалист поддержки"],
    "Маркетинг":  ["Маркетолог"],
    "HR":         ["HR-менеджер"],
}
RUNS = 3                 # волны (запуски)
RUN_GAP_DAYS = 90        # ~квартал между волнами
RESP_PER_RUN = 8         # >= гейта анонимности N>=5
EMP_PER_DEPT = 8

# Вовлечённость по отделам ОТ ВОЛНЫ К ВОЛНЕ (1–5). «Продажи» проседают — драматургия демо.
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
        titles = TITLES[dept]
        for i in range(EMP_PER_DEPT):
            emp, created = Employee.objects.get_or_create(
                phone=f"+7900{di}{i:03d}",
                defaults={"name": f"{dept} {i+1}", "role": Employee.EMPLOYEE,
                          "department": dept, "city": CITIES[i % len(CITIES)],
                          "job_title": titles[i % len(titles)], "consent_at": timezone.now()},
            )
            if not created:
                emp.city = CITIES[i % len(CITIES)]
                emp.job_title = titles[i % len(titles)]
                emp.save(update_fields=["city", "job_title"])
            employees[dept].append(emp)

    # --- опрос (определение) ---
    Survey.objects.filter(title="Пульс-опрос вовлечённости").delete()
    survey = Survey.objects.create(
        title="Пульс-опрос вовлечённости", description="Регулярный pulse-мониторинг настроения.",
        mode=Survey.ANONYMOUS, status=Survey.ACTIVE,
        starts_at=timezone.now(), ends_at=timezone.now() + timedelta(days=10),
    )
    q_eng = Question.objects.create(survey=survey, order=1, qtype=Question.SCALE,
        text="Оцените вовлечённость", config={"min": 1, "max": 5, "low": "Низкая", "high": "Высокая"})
    q_nps = Question.objects.create(survey=survey, order=2, qtype=Question.SCALE,
        text="Порекомендуете компанию как место работы?", config={"min": 0, "max": 10, "nps": True})
    q_choice = Question.objects.create(survey=survey, order=3, qtype=Question.SINGLE,
        text="Что больше всего мешает в работе?", config={"options": CHOICES})
    q_text = Question.objects.create(survey=survey, order=4, qtype=Question.TEXT,
        text="Что бы вы изменили?", required=False)

    # --- волны (запуски) с backdated ответами ---
    now = timezone.now()
    for ri in range(RUNS):
        run_dt = now - timedelta(days=RUN_GAP_DAYS * (RUNS - 1 - ri))
        is_last = ri == RUNS - 1
        run_obj = SurveyRun.objects.create(
            survey=survey, index=ri + 1,
            status=SurveyRun.ACTIVE if is_last else SurveyRun.COMPLETED,
            starts_at=run_dt, ends_at=run_dt + timedelta(days=10 if is_last else 7),
        )
        for dept in DEPTS:
            eng_mean = ENG[dept][ri]
            for _ in range(RESP_PER_RUN):
                r = Response.objects.create(
                    run=run_obj, survey=survey, department=dept, session_id="seed",
                    city=random.choice(CITIES), job_title=random.choice(TITLES[dept]))
                Response.objects.filter(pk=r.pk).update(submitted_at=run_dt)
                eng = max(1, min(5, round(random.gauss(eng_mean, 0.5))))
                nps = max(0, min(10, round(random.gauss(eng_mean * 2, 1.5))))
                Answer.objects.create(response=r, question=q_eng, value_num=eng)
                Answer.objects.create(response=r, question=q_nps, value_num=nps)
                weights = [5, 2, 2, 1, 1] if dept == "Продажи" and eng <= 3 else [1, 2, 1, 2, 4]
                Answer.objects.create(response=r, question=q_choice,
                                      value_json=random.choices(CHOICES, weights=weights)[0])
                Answer.objects.create(response=r, question=q_text,
                                      value_text=random.choice(NEG if eng <= 3 else POS))
        # участия per-run (~70%); в активной волне часть не прошли — чтобы можно было пройти на демо
        for dept in DEPTS:
            for emp in employees[dept]:
                if random.random() < 0.7:
                    Participation.objects.get_or_create(run=run_obj, survey=survey, employee=emp)

    survey.sync_status()
    print(f"Seed готов: survey #{survey.id} «{survey.title}», {RUNS} волн × {len(DEPTS)} отделов, "
          f"{Employee.objects.count()} аккаунтов.")


if __name__ == "__main__":
    run()
