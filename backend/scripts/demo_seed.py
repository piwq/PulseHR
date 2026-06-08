"""Расширенный наполнитель БД демо-данными.

Создаёт сотрудников и НЕСКОЛЬКО опросов на все типы вопросов (single / multi / scale / NPS /
text / matrix), с ветвлением, в разных режимах и статусах, со сгенерированными ответами и
участиями. Подходит для демонстрации конструктора, прохождения и аналитики.

Запуск:  docker compose exec core python scripts/demo_seed.py
Идемпотентно: опросы с теми же названиями пересоздаются.
"""
import os
import random
import sys
from datetime import timedelta

import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.utils import timezone  # noqa: E402

from apps.accounts.models import Employee  # noqa: E402
from apps.surveys.models import (Answer, Participation, Question,  # noqa: E402
                                 Response, Survey)

DEPTS = ["Продажи", "Разработка", "Поддержка", "Маркетинг", "HR"]
EMP_PER_DEPT = 8

TEXT_POS = ["Всё нравится, команда отличная.", "Интересные задачи, хочу развиваться.",
            "В целом доволен, спасибо за условия."]
TEXT_NEG = ["Слишком много переработок.", "Не хватает обратной связи.",
            "Зарплата ниже рынка.", "Хочется больше гибкости в графике."]

# ---------------------------------------------------------------- определения опросов
# branch: None | {"question": <order>, "op": eq|ne|lte|gte|in, "value": ...}
SURVEYS = [
    {
        "title": "Пульс: вовлечённость",
        "mode": "anonymous", "status": "active", "critical": False, "waves": 3,
        "questions": [
            {"text": "Насколько вам нравится работать в компании?", "qtype": "scale",
             "config": {"min": 1, "max": 5, "low": "Совсем нет", "high": "Очень нравится"}},
            {"text": "Порекомендуете компанию друзьям как место работы?", "qtype": "scale",
             "config": {"min": 0, "max": 10, "nps": True}},
            {"text": "Что мотивирует вас больше всего?", "qtype": "single",
             "config": {"options": ["Зарплата", "Команда", "Задачи", "Развитие", "Признание"]}},
            {"text": "Что хотелось бы улучшить?", "qtype": "multi",
             "config": {"options": ["Процессы", "Коммуникация", "Условия", "График", "Зарплата"]}},
            {"text": "Что бы вы изменили в работе команды?", "qtype": "text", "required": False},
        ],
    },
    {
        "title": "Адаптация: рабочее место (с ветвлением)",
        "mode": "identified", "status": "active", "critical": False,
        "questions": [
            {"text": "Ваша должность?", "qtype": "single",
             "config": {"options": ["Товаровед", "Руководитель", "Офисный сотрудник"]}},
            {"text": "Оцените удобство рабочего места", "qtype": "scale",
             "config": {"min": 1, "max": 5}, "branch": {"question": 1, "op": "eq", "value": "Товаровед"}},
            {"text": "Что именно неудобно?", "qtype": "text", "required": False,
             "branch": {"question": 2, "op": "lte", "value": 2}},
            {"text": "Оцените качество управления командой", "qtype": "scale",
             "config": {"min": 1, "max": 5}, "branch": {"question": 1, "op": "eq", "value": "Руководитель"}},
            {"text": "Комфортна ли офисная среда?", "qtype": "scale",
             "config": {"min": 1, "max": 5}, "branch": {"question": 1, "op": "eq", "value": "Офисный сотрудник"}},
        ],
    },
    {
        "title": "Условия труда (матрица)",
        "mode": "anonymous", "status": "active", "critical": False,
        "questions": [
            {"text": "Оцените условия на рабочем месте", "qtype": "matrix",
             "config": {"rows": ["Освещение", "Температура", "Шум", "Мебель"],
                        "cols": ["Плохо", "Нормально", "Хорошо"]}},
            {"text": "Как часто перерабатываете?", "qtype": "single",
             "config": {"options": ["Никогда", "Иногда", "Часто", "Постоянно"]}},
            {"text": "Комментарий", "qtype": "text", "required": False},
        ],
    },
    {
        "title": "Итоги квартала Q1",
        "mode": "anonymous", "status": "completed", "critical": False,
        "questions": [
            {"text": "Насколько вы довольны прошедшим кварталом?", "qtype": "scale",
             "config": {"min": 1, "max": 5}},
            {"text": "Порекомендуете компанию?", "qtype": "scale", "config": {"min": 0, "max": 10, "nps": True}},
        ],
    },
    {
        "title": "360-оценка (черновик)",
        "mode": "identified", "status": "draft", "critical": False,
        "questions": [
            {"text": "Оцените коллегу по шкале", "qtype": "scale", "config": {"min": 1, "max": 5}},
            {"text": "Сильные стороны", "qtype": "text", "required": False},
        ],
    },
]


# ---------------------------------------------------------------- helpers
def ensure_employees():
    Employee.objects.get_or_create(
        phone="+79990000000",
        defaults={"name": "Анна Котова", "role": Employee.HR, "department": "HR",
                  "consent_at": timezone.now()})
    by_dept = {d: [] for d in DEPTS}
    for di, dept in enumerate(DEPTS):
        for i in range(EMP_PER_DEPT):
            emp, _ = Employee.objects.get_or_create(
                phone=f"+7900{di}{i:03d}",
                defaults={"name": f"{dept} {i+1}", "role": Employee.EMPLOYEE,
                          "department": dept, "consent_at": timezone.now()})
            by_dept[dept].append(emp)
    return by_dept


def create_survey(d):
    Survey.objects.filter(title=d["title"]).delete()
    now = timezone.now()
    s = Survey.objects.create(
        title=d["title"], description="Демо-опрос.", mode=d["mode"], status=d["status"],
        critical=d["critical"], is_active=d["status"] == "active",
        starts_at=now - timedelta(days=30),
        ends_at=now + (timedelta(days=10) if d["status"] == "active" else timedelta(days=-2)))
    questions = []
    for i, q in enumerate(d["questions"]):
        questions.append(Question.objects.create(
            survey=s, order=i + 1, text=q["text"], qtype=q["qtype"],
            required=q.get("required", True), config=q.get("config", {}),
            branch_rules={"show_if": q["branch"]} if q.get("branch") else {}))
    return s, questions


def visible(q, answers):
    r = q.branch_rules.get("show_if")
    if not r:
        return True
    val = answers.get(r["question"])
    if val is None:
        return False
    op, t = r["op"], r["value"]
    if op == "eq":
        return str(val) == str(t)
    if op == "ne":
        return str(val) != str(t)
    if op == "lte":
        return float(val) <= float(t)
    if op == "gte":
        return float(val) >= float(t)
    if op == "in":
        return val in t
    return True


def sample_value(q, dept, wave_bias=0.0):
    c = q.config
    if q.qtype == "scale":
        if c.get("nps"):
            return max(0, min(10, round(random.gauss(7 - wave_bias * 2, 1.6))))
        mn, mx = c.get("min", 1), c.get("max", 5)
        return max(mn, min(mx, round(random.gauss(3.8 - wave_bias, 0.8))))
    if q.qtype == "single":
        opts = c["options"]
        # лёгкий перекос для «Продаж» к негативу там, где он есть
        if dept == "Продажи" and "Постоянно" in opts:
            return random.choices(opts, weights=[1, 2, 3, 4])[0]
        return random.choice(opts)
    if q.qtype == "multi":
        opts = c["options"]
        return random.sample(opts, k=random.randint(1, min(3, len(opts))))
    if q.qtype == "matrix":
        return {row: random.choice(c["cols"]) for row in c["rows"]}
    if q.qtype == "text":
        return random.choice(TEXT_NEG if wave_bias > 0.4 else TEXT_POS)
    return None


def write_answers(response, questions, dept, wave_bias=0.0):
    answers = {}
    for q in questions:
        if not visible(q, answers):
            continue
        if not q.required and random.random() < 0.3:
            continue  # часть необязательных пропускаем
        v = sample_value(q, dept, wave_bias)
        answers[q.order] = v
        if q.qtype == "scale":
            Answer.objects.create(response=response, question=q, value_num=v)
        elif q.qtype == "text":
            Answer.objects.create(response=response, question=q, value_text=v)
        else:
            Answer.objects.create(response=response, question=q, value_json=v)


def fill_survey(s, questions, by_dept):
    now = timezone.now()
    if s.status == "draft":
        return
    waves = next((d.get("waves", 1) for d in SURVEYS if d["title"] == s.title), 1)

    if s.mode == "identified":
        # уникальные сотрудники, ответы привязаны к employee + Participation
        for dept in DEPTS:
            for emp in random.sample(by_dept[dept], k=6):
                r = Response.objects.create(survey=s, employee=emp, department=dept)
                write_answers(r, questions, dept)
                Participation.objects.get_or_create(survey=s, employee=emp)
    else:
        # анонимно: ответы с session_id, без employee; волны для тренда
        for wave in range(waves):
            when = now - timedelta(days=14 * (waves - wave))
            bias = (wave / max(1, waves - 1)) if waves > 1 else 0.0  # рост негатива к последней волне
            for dept in DEPTS:
                dept_bias = bias if dept == "Продажи" else bias * 0.2
                for _ in range(8):
                    r = Response.objects.create(survey=s, department=dept, session_id="demo")
                    Response.objects.filter(pk=r.pk).update(submitted_at=when)
                    write_answers(r, questions, dept, dept_bias)
        # участия для % прохождения
        for dept in DEPTS:
            for emp in by_dept[dept]:
                if random.random() < 0.7:
                    Participation.objects.get_or_create(survey=s, employee=emp)


def run():
    by_dept = ensure_employees()
    created = []
    for d in SURVEYS:
        s, questions = create_survey(d)
        fill_survey(s, questions, by_dept)
        created.append((s, len(questions)))
    print("Демо-данные созданы:")
    for s, qn in created:
        print(f"  #{s.id} «{s.title}» [{s.mode}/{s.status}] — {qn} вопросов, "
              f"{s.responses.count()} ответов, {s.participations.count()} участий")
    print(f"Всего аккаунтов: {Employee.objects.count()}")


if __name__ == "__main__":
    run()
