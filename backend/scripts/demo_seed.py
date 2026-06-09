"""Презентационный наполнитель БД — БОЛЬШИЕ реалистичные данные для демо.

Создаёт:
- компанию ~160 сотрудников: 8 отделов, 5 городов, должности (для богатых фильтров и гейта N>=5);
- флагманский pulse-опрос вовлечённости с 5 ВОЛНАМИ (кварталы) и трендами по отделам
  (Продажи/Операции/Поддержка проседают → драматургия + сравнение волн);
- набор опросов на все типы вопросов (single/multi/scale/NPS/text/matrix), ветвление,
  оба режима (анонимный/идентифицированный) и все статусы (черновик/активный/завершён/архив);
- журнал уведомлений по каналам (Web Push/Telegram/SMS/Email) со статусами и стоимостью —
  чтобы дашборд «Каналы» показывал живые CTR / стоимость SMS / время до прохождения;
- инсайты на проблемных отделах для дашборда и алертов.

Запуск:  docker compose exec core python scripts/demo_seed.py
Идемпотентно: полностью пересоздаёт демо-данные (опросы и рядовых сотрудников).
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
from apps.insights.models import Insight  # noqa: E402
from apps.notifications.models import NotificationLog  # noqa: E402
from apps.surveys.models import (Answer, Participation, Question,  # noqa: E402
                                 Response, Survey, SurveyRun)

random.seed(7)  # воспроизводимость демо

# ── Справочники ─────────────────────────────────────────────────────────────
DEPARTMENTS = ["Продажи", "Разработка", "Поддержка", "Маркетинг",
               "HR", "Финансы", "Логистика", "Операции"]
SIZE = {"Продажи": 34, "Разработка": 26, "Поддержка": 22, "Маркетинг": 14,
        "HR": 10, "Финансы": 12, "Логистика": 20, "Операции": 24}
CITIES = ["Москва", "Санкт-Петербург", "Казань", "Екатеринбург", "Новосибирск"]
CITY_W = [0.40, 0.22, 0.15, 0.13, 0.10]
TITLES = {
    "Продажи":    ["Менеджер по продажам", "Старший менеджер", "Руководитель группы"],
    "Разработка": ["Разработчик", "Старший разработчик", "Тимлид"],
    "Поддержка":  ["Специалист поддержки", "Старший специалист"],
    "Маркетинг":  ["Маркетолог", "Бренд-менеджер"],
    "HR":         ["HR-специалист", "Рекрутёр"],
    "Финансы":    ["Финансовый аналитик", "Бухгалтер"],
    "Логистика":  ["Логист", "Кладовщик", "Водитель"],
    "Операции":   ["Оператор", "Супервайзер"],
}
FIRST = ["Александр", "Сергей", "Дмитрий", "Андрей", "Алексей", "Максим", "Иван", "Михаил",
         "Никита", "Егор", "Анна", "Мария", "Елена", "Ольга", "Наталья", "Екатерина",
         "Татьяна", "Ирина", "Юлия", "Светлана", "Павел", "Роман", "Артём", "Денис",
         "Виктор", "Олег", "Кирилл", "Дарья", "Ксения", "Полина"]
LAST = ["Иванов", "Петров", "Смирнов", "Кузнецов", "Соколов", "Попов", "Лебедев", "Козлов",
        "Новиков", "Морозов", "Волков", "Алексеев", "Фёдоров", "Михайлов", "Никитин", "Орлов",
        "Макаров", "Захаров", "Зайцев", "Соловьёв", "Борисов", "Яковлев", "Григорьев",
        "Романов", "Воробьёв", "Сергеев", "Кузьмин", "Фролов", "Беляев", "Комаров"]

# Вовлечённость по отделам ОТ ВОЛНЫ К ВОЛНЕ (5 кварталов, 1–5).
ENG_TRAJ = {
    "Продажи":    [4.1, 3.8, 3.3, 2.9, 2.5],
    "Разработка": [3.7, 3.9, 4.0, 4.1, 4.2],
    "Поддержка":  [3.9, 3.7, 3.6, 3.4, 3.2],
    "Маркетинг":  [3.8, 3.7, 3.9, 3.8, 3.9],
    "HR":         [4.0, 4.1, 4.0, 4.1, 4.2],
    "Финансы":    [3.7, 3.6, 3.7, 3.6, 3.5],
    "Логистика":  [3.4, 3.5, 3.3, 3.6, 3.7],
    "Операции":   [3.8, 3.7, 3.5, 3.4, 3.2],
}
BLOCK = ["Переработки", "Зарплата", "Отношения с руководством",
         "Нехватка ресурсов", "Рутинные задачи", "Ничего не мешает"]
IMPROVE = ["Процессы", "Коммуникация", "Условия труда", "График", "Обучение", "Признание"]
NEG = ["Постоянные переработки, не успеваю восстанавливаться.",
       "Горят сроки, задач больше, чем рук.",
       "Не хватает обратной связи от руководителя.",
       "Выгораю, всерьёз думаю о смене работы.",
       "Зарплата давно не пересматривалась.",
       "Много рутины, нет роста."]
NEU = ["В целом нормально, но нагрузка высокая.",
       "Команда хорошая, процессы хромают.",
       "Терпимо, хотелось бы больше ясности по целям."]
POS = ["Нравятся задачи и команда, всё устраивает.",
       "Хорошие условия, чувствую поддержку руководителя.",
       "Интересные проекты, есть куда расти."]


def gi(mean, lo=1, hi=5):
    return max(lo, min(hi, round(random.gauss(mean, 0.7))))


def gnps(mean):
    # центр шкалы 0–10 коррелирует с вовлечённостью: здоровые отделы → положительный eNPS,
    # проблемные → отрицательный (плавный градиент для демо).
    return max(0, min(10, round(random.gauss(mean * 2 + 0.3, 1.6))))


def pick_block(dept, eng):
    if eng <= 2:
        w = [6, 3, 5, 3, 2, 0]
    elif eng == 3:
        w = [4, 3, 3, 2, 3, 1]
    else:
        w = [1, 2, 1, 1, 2, 6]
    if dept == "Продажи":
        w[0] += 3
    if dept == "Операции":
        w[0] += 2
    return random.choices(BLOCK, weights=w)[0]


def pick_comment(eng):
    pool = NEG if eng <= 2 else (NEU if eng == 3 else POS)
    return random.choice(pool)


def weighted_city():
    return random.choices(CITIES, weights=CITY_W)[0]


# ── Сотрудники ──────────────────────────────────────────────────────────────
def make_employees():
    Survey.objects.all().delete()          # каскадом снесёт волны/ответы/участия/логи/инсайты
    Employee.objects.filter(role=Employee.EMPLOYEE).delete()
    Employee.objects.update_or_create(
        phone="+79990000000",
        defaults={"name": "Анна Котова", "role": Employee.HR, "department": "HR",
                  "city": "Москва", "job_title": "Директор по персоналу",
                  "consent_at": timezone.now()})

    by_dept = {}
    serial = 1_000_000
    for dept in DEPARTMENTS:
        batch = []
        for _ in range(SIZE[dept]):
            serial += 1
            batch.append(Employee(
                phone=f"+7901{serial}", name=f"{random.choice(FIRST)} {random.choice(LAST)}",
                role=Employee.EMPLOYEE, department=dept, city=weighted_city(),
                job_title=random.choice(TITLES[dept]), consent_at=timezone.now()))
        Employee.objects.bulk_create(batch)
        by_dept[dept] = list(Employee.objects.filter(role=Employee.EMPLOYEE, department=dept))
    total = sum(len(v) for v in by_dept.values())
    print(f"  сотрудников: {total} в {len(DEPARTMENTS)} отделах, {len(CITIES)} городах")
    return by_dept


def _new_run(survey, idx, status, dt, days=14):
    return SurveyRun.objects.create(
        survey=survey, index=idx, status=status,
        starts_at=dt, ends_at=dt + timedelta(days=days))


# ── Флагманский pulse-опрос (5 волн) ────────────────────────────────────────
def make_pulse(by_dept):
    now = timezone.now()
    s = Survey.objects.create(
        title="Пульс вовлечённости", mode=Survey.ANONYMOUS, status=Survey.ACTIVE,
        description="Ежеквартальный мониторинг вовлечённости, eNPS и настроения команд.",
        starts_at=now, ends_at=now + timedelta(days=10))
    q_eng = Question.objects.create(survey=s, order=1, qtype=Question.SCALE,
        text="Насколько вы вовлечены в работу?", config={"min": 1, "max": 5, "low": "Совсем нет", "high": "Полностью"})
    q_nps = Question.objects.create(survey=s, order=2, qtype=Question.SCALE,
        text="Порекомендуете компанию как место работы?", config={"min": 0, "max": 10, "nps": True})
    q_blk = Question.objects.create(survey=s, order=3, qtype=Question.SINGLE,
        text="Что сильнее всего мешает в работе?", config={"options": BLOCK})
    q_imp = Question.objects.create(survey=s, order=4, qtype=Question.MULTI,
        text="Что улучшить в первую очередь?", config={"options": IMPROVE})
    q_txt = Question.objects.create(survey=s, order=5, qtype=Question.TEXT,
        text="Что бы вы изменили?", required=False)

    waves = len(ENG_TRAJ["Продажи"])
    last_run = None
    for wi in range(waves):
        is_last = wi == waves - 1
        start = now - timedelta(days=90 * (waves - 1 - wi) + 16)
        run = _new_run(s, wi + 1, SurveyRun.ACTIVE if is_last else SurveyRun.COMPLETED,
                       start, days=(10 if is_last else 12))
        last_run = run

        span = 12 if is_last else 8
        resp, meta = [], []
        for dept, emps in by_dept.items():
            n = int(len(emps) * random.uniform(0.72, 0.86))
            for emp in random.sample(emps, n):
                t = random.random()  # позиция ответа внутри окна волны (0..1)
                # активная волна: вовлечённость плавно дрейфует от прошлой волны к текущей
                # (тренд внутри волны направленный, а не шумовой) → нет ложных critical
                if is_last:
                    m0, m1 = ENG_TRAJ[dept][wi - 1], ENG_TRAJ[dept][wi]
                    mean = m0 + (m1 - m0) * t
                else:
                    mean = ENG_TRAJ[dept][wi]
                resp.append(Response(run=run, survey=s, department=dept, session_id="demo",
                                     city=emp.city, job_title=emp.job_title))
                meta.append((emp, dept, mean, t))
        Response.objects.bulk_create(resp)
        for r, (emp, dept, mean, t) in zip(resp, meta):
            r.submitted_at = start + timedelta(days=t * span, minutes=random.randint(0, 800))
        Response.objects.bulk_update(resp, ["submitted_at"])

        ans, parts = [], []
        for r, (emp, dept, mean, t) in zip(resp, meta):
            eng = max(1, min(5, round(random.gauss(mean, 0.55))))
            ans.append(Answer(response=r, question=q_eng, value_num=eng))
            ans.append(Answer(response=r, question=q_nps, value_num=gnps(mean)))
            ans.append(Answer(response=r, question=q_blk, value_json=pick_block(dept, eng)))
            ans.append(Answer(response=r, question=q_imp,
                              value_json=random.sample(IMPROVE, random.randint(1, 3))))
            if random.random() < 0.6:
                ans.append(Answer(response=r, question=q_txt, value_text=pick_comment(eng)))
            parts.append(Participation(run=run, survey=s, employee=emp))
        Answer.objects.bulk_create(ans)
        Participation.objects.bulk_create(parts, ignore_conflicts=True)
        Participation.objects.filter(run=run).update(completed_at=run.starts_at + timedelta(days=3))

    make_notifications(s, last_run, by_dept)
    seed_insights(s, last_run)
    s.sync_status()
    return s


# ── Уведомления по каналам (для дашборда «Каналы») ──────────────────────────
def make_notifications(survey, run, by_dept):
    audience = [e for emps in by_dept.values() for e in emps]
    comp = dict(Participation.objects.filter(run=run).values_list("employee_id", "completed_at"))
    channels = [("push", 0.70), ("telegram", 0.15), ("sms", 0.10), ("email", 0.05)]
    delay_min = {"push": (5, 180), "telegram": (60, 480), "sms": (240, 1440), "email": (480, 2160)}
    logs, sent_ats = [], []
    for emp in audience:
        ch = random.choices([c for c, _ in channels], weights=[w for _, w in channels])[0]
        if emp.id in comp:  # дошёл до прохождения
            lo, hi = delay_min[ch]
            sent = comp[emp.id] - timedelta(minutes=random.randint(lo, hi))
            status = NotificationLog.CLICKED if random.random() < 0.72 else NotificationLog.OPENED
        else:               # уведомление ушло, но не прошёл
            sent = timezone.now() - timedelta(hours=random.randint(2, 96))
            status = NotificationLog.OPENED if random.random() < 0.32 else NotificationLog.SENT
        logs.append(NotificationLog(
            employee=emp, run=run, survey=survey, channel=ch, status=status,
            cost=5 if ch == "sms" else 0, dedup_key=f"{run.id}:{emp.id}:{ch}"))
        sent_ats.append(sent)
    NotificationLog.objects.bulk_create(logs)
    for log_obj, sent in zip(logs, sent_ats):
        log_obj.created_at = sent
    NotificationLog.objects.bulk_update(logs, ["created_at"])
    print(f"  уведомлений: {len(logs)} (push/telegram/sms/email) на активной волне")


def seed_insights(survey, run):
    spec = [("Продажи", 3, "вовлечённость падает 4 волны подряд, eNPS ушёл в минус. Топ-причина — переработки и нехватка ресурсов."),
            ("Операции", 2, "снижение вовлечённости и рост жалоб на руководство."),
            ("Поддержка", 2, "медленное, но устойчивое падение вовлечённости.")]
    for dept, sev, why in spec:
        Insight.objects.create(survey=survey, run=run, department=dept, severity=sev,
                               summary=f"Отдел «{dept}»: {why}", tg_sent=True)


# ── Прочие опросы (все типы/режимы/статусы) ─────────────────────────────────
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


def sample_value(q, mean):
    c = q.config
    if q.qtype == "scale":
        return gnps(mean) if c.get("nps") else gi(mean, c.get("min", 1), c.get("max", 5))
    if q.qtype == "single":
        return random.choice(c["options"])
    if q.qtype == "multi":
        opts = c["options"]
        return random.sample(opts, random.randint(1, min(3, len(opts))))
    if q.qtype == "matrix":
        cols = c["cols"]
        w = [i + 1 for i in range(len(cols))] if mean >= 3.5 else [len(cols) - i for i in range(len(cols))]
        return {row: random.choices(cols, weights=w)[0] for row in c["rows"]}
    if q.qtype == "text":
        return pick_comment(round(mean))
    return None


def gen_wave(survey, run, questions, by_dept, mean_for, identified, frac):
    resp, meta = [], []
    for dept, emps in by_dept.items():
        if identified:
            sample = random.sample(emps, max(1, int(len(emps) * frac)))
            for emp in sample:
                resp.append(Response(run=run, survey=survey, employee=emp, department=dept,
                                     city=emp.city, job_title=emp.job_title))
                meta.append((emp, dept))
        else:
            for _ in range(max(1, int(len(emps) * frac))):
                emp = random.choice(emps)
                resp.append(Response(run=run, survey=survey, department=dept, session_id="demo",
                                     city=emp.city, job_title=emp.job_title))
                meta.append((emp, dept))
    Response.objects.bulk_create(resp)
    for r in resp:
        r.submitted_at = run.starts_at + timedelta(days=random.randint(0, 9), minutes=random.randint(0, 900))
    Response.objects.bulk_update(resp, ["submitted_at"])

    ans, parts = [], []
    for r, (emp, dept) in zip(resp, meta):
        mean = mean_for(dept)
        adict = {}
        for q in questions:
            if not visible(q, adict):
                continue
            if not q.required and random.random() < 0.25:
                continue
            v = sample_value(q, mean)
            adict[q.order] = v
            if q.qtype == "scale":
                ans.append(Answer(response=r, question=q, value_num=v))
            elif q.qtype == "text":
                ans.append(Answer(response=r, question=q, value_text=v))
            else:
                ans.append(Answer(response=r, question=q, value_json=v))
        if identified:
            parts.append(Participation(run=run, survey=survey, employee=emp))
    Answer.objects.bulk_create(ans)
    if not identified:
        for dept, emps in by_dept.items():
            for emp in emps:
                if random.random() < frac:
                    parts.append(Participation(run=run, survey=survey, employee=emp))
    Participation.objects.bulk_create(parts, ignore_conflicts=True)
    Participation.objects.filter(run=run).update(completed_at=run.starts_at + timedelta(days=2))


OTHERS = [
    {"title": "Удовлетворённость руководством", "mode": "anonymous", "status": "completed",
     "means": [3.6, 3.3, 3.0], "frac": 0.7, "questions": [
        {"text": "Оцените работу вашего руководителя", "qtype": "scale", "config": {"min": 1, "max": 5}},
        {"text": "Порекомендуете ли своего руководителя?", "qtype": "scale", "config": {"min": 0, "max": 10, "nps": True}},
        {"text": "Что улучшить в управлении командой?", "qtype": "text", "required": False}]},
    {"title": "Условия труда на местах", "mode": "anonymous", "status": "active",
     "means": [3.5, 3.4], "frac": 0.65, "questions": [
        {"text": "Оцените условия на рабочем месте", "qtype": "matrix",
         "config": {"rows": ["Освещение", "Температура", "Шум", "Мебель", "Техника"],
                    "cols": ["Плохо", "Нормально", "Хорошо"]}},
        {"text": "Как часто перерабатываете?", "qtype": "single",
         "config": {"options": ["Никогда", "Иногда", "Часто", "Постоянно"]}},
        {"text": "Комментарий по условиям", "qtype": "text", "required": False}]},
    {"title": "Адаптация новых сотрудников", "mode": "identified", "status": "active",
     "means": [3.8], "frac": 0.45, "questions": [
        {"text": "Ваша должность?", "qtype": "single",
         "config": {"options": ["Товаровед", "Руководитель", "Офисный сотрудник"]}},
        {"text": "Оцените удобство рабочего места", "qtype": "scale", "config": {"min": 1, "max": 5},
         "branch": {"question": 1, "op": "eq", "value": "Товаровед"}},
        {"text": "Что именно неудобно?", "qtype": "text", "required": False,
         "branch": {"question": 2, "op": "lte", "value": 2}},
        {"text": "Оцените качество управления командой", "qtype": "scale", "config": {"min": 1, "max": 5},
         "branch": {"question": 1, "op": "eq", "value": "Руководитель"}},
        {"text": "Комфортна ли офисная среда?", "qtype": "scale", "config": {"min": 1, "max": 5},
         "branch": {"question": 1, "op": "eq", "value": "Офисный сотрудник"}}]},
    {"title": "Выходное интервью", "mode": "identified", "status": "active", "critical": True,
     "means": [2.8], "frac": 0.12, "questions": [
        {"text": "Насколько комфортно было работать в компании?", "qtype": "scale", "config": {"min": 1, "max": 5}},
        {"text": "Главная причина ухода?", "qtype": "single",
         "config": {"options": ["Зарплата", "Руководство", "Нагрузка", "Нет роста", "Релокация"]}},
        {"text": "Что стоит улучшить в компании?", "qtype": "text", "required": False}]},
    {"title": "Оценка корпоративного обучения", "mode": "anonymous", "status": "completed",
     "means": [4.0], "frac": 0.6, "questions": [
        {"text": "Насколько полезным было обучение?", "qtype": "scale", "config": {"min": 1, "max": 5}},
        {"text": "Какие темы интересны?", "qtype": "multi",
         "config": {"options": ["Лидерство", "Продажи", "Технологии", "Софт-скиллы", "Финансы"]}},
        {"text": "Пожелания по программе", "qtype": "text", "required": False}]},
    {"title": "360-оценка коллег (черновик)", "mode": "identified", "status": "draft",
     "means": [3.8], "frac": 0.0, "questions": [
        {"text": "Оцените коллегу по шкале", "qtype": "scale", "config": {"min": 1, "max": 5}},
        {"text": "Сильные стороны", "qtype": "text", "required": False}]},
]


def make_other(spec, by_dept):
    now = timezone.now()
    s = Survey.objects.create(
        title=spec["title"], mode=spec["mode"], status=spec["status"],
        critical=spec.get("critical", False), description="Демо-опрос.",
        starts_at=now - timedelta(days=20), ends_at=now + timedelta(days=8))
    questions = [Question.objects.create(
        survey=s, order=i + 1, text=q["text"], qtype=q["qtype"],
        required=q.get("required", True), config=q.get("config", {}),
        branch_rules={"show_if": q["branch"]} if q.get("branch") else {})
        for i, q in enumerate(spec["questions"])]

    if spec["status"] != "draft":
        means = spec["means"]
        for wi, mean in enumerate(means):
            is_last = wi == len(means) - 1
            if spec["status"] == "completed":
                st = SurveyRun.COMPLETED
            elif spec["status"] == "archive":
                st = SurveyRun.ARCHIVE
            else:
                st = SurveyRun.ACTIVE if is_last else SurveyRun.COMPLETED
            start = now - timedelta(days=70 * (len(means) - 1 - wi) + 14)
            run = _new_run(s, wi + 1, st, start, days=12)
            gen_wave(s, run, questions, by_dept,
                     mean_for=lambda dept, m=mean: m + (-0.4 if dept == "Продажи" else random.uniform(-0.2, 0.2)),
                     identified=(spec["mode"] == "identified"), frac=spec["frac"])
    s.sync_status()
    return s


def make_demo_takers():
    """Сотрудники с запоминающимися номерами для живого прохождения опросов на демо.

    Создаются ПОСЛЕ генерации (не попадают в выборки) → нет участий → могут пройти
    активные опросы вживую (в т.ч. анонимный pulse и идентифицированные).
    """
    takers = [
        ("+79001112233", "Иван Демидов", "Продажи", "Москва", "Менеджер по продажам"),
        ("+79001114455", "Ольга Демина", "Поддержка", "Казань", "Специалист поддержки"),
    ]
    for phone, name, dept, city, title in takers:
        Employee.objects.update_or_create(phone=phone, defaults={
            "name": name, "role": Employee.EMPLOYEE, "department": dept,
            "city": city, "job_title": title, "consent_at": timezone.now()})
    print(f"  демо-логины для прохождения: {', '.join(t[0] for t in takers)}")


def run():
    print("Презентационный seed PulseHR…")
    by_dept = make_employees()
    pulse = make_pulse(by_dept)
    print(f"  #{pulse.id} «{pulse.title}» — {pulse.runs.count()} волн, "
          f"{pulse.responses.count()} ответов, {pulse.participations.count()} участий")
    for spec in OTHERS:
        s = make_other(spec, by_dept)
        print(f"  #{s.id} «{s.title}» [{s.mode}/{s.status}] — {s.runs.count()} волн, "
              f"{s.responses.count()} ответов")
    make_demo_takers()
    print(f"Готово. Опросов: {Survey.objects.count()}, аккаунтов: {Employee.objects.count()}, "
          f"ответов всего: {Response.objects.count()}, лог уведомлений: {NotificationLog.objects.count()}")


if __name__ == "__main__":
    run()
