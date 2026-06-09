"""Аналитика волны опроса (SurveyRun): вовлечённость, eNPS, разбивка по отделам, тренд,
распределение, по дням, комментарии. Все функции работают на одной ВОЛНЕ (run).
Гейт анонимности N>=5 защищает от деанонимизации сегментов."""
from collections import defaultdict
from statistics import mean

from apps.accounts.models import Employee

from .models import Answer, Participation, Question

MIN_SEGMENT = 5  # гейт анонимности: агрегат по сегменту только при N>=5


def _seg(qs, field, val):
    """Применить сегментный фильтр: скаляр → точное равенство, список → __in."""
    if not val:
        return qs
    if isinstance(val, (list, tuple, set)):
        return qs.filter(**{f"{field}__in": list(val)})
    return qs.filter(**{field: val})


def filtered_responses(run, department=None, city=None, job_title=None):
    """Ответы волны с опциональным фильтром по сегментам (отдел/город/должность)."""
    qs = run.responses.all()
    qs = _seg(qs, "department", department)
    qs = _seg(qs, "city", city)
    qs = _seg(qs, "job_title", job_title)
    return qs


def filter_values(run):
    """Списки доступных значений фильтров (для дропдаунов на дашборде)."""
    rows = run.responses.values_list("department", "city", "job_title")
    depts, cities, titles = set(), set(), set()
    for d, c, j in rows:
        if d:
            depts.add(d)
        if c:
            cities.add(c)
        if j:
            titles.add(j)
    return {
        "departments": sorted(depts),
        "cities": sorted(cities),
        "job_titles": sorted(titles),
    }


def _scale_question_ids(survey, nps=None):
    qs = survey.questions.filter(qtype=Question.SCALE)
    return [q.id for q in qs if (nps is None or bool(q.config.get("nps")) == nps)]


def engagement(answer_qs):
    vals = [a.value_num for a in answer_qs if a.value_num is not None]
    return round(mean(vals), 2) if vals else None


def enps_from(values):
    """eNPS = %промоутеров(9–10) − %критиков(0–6) по шкале 0–10."""
    if not values:
        return None
    n = len(values)
    promoters = sum(1 for v in values if v >= 9)
    detractors = sum(1 for v in values if v <= 6)
    return round((promoters - detractors) / n * 100)


def severity_for(eng, drop=None):
    """Severity по абсолютному уровню вовлечённости (1–5). Падение во времени —
    отдельный сигнал (дельта к прошлой волне / сравнение волн), не зашумляет severity."""
    if eng is None:
        return "low"
    if eng < 3.0:
        return "critical"
    if eng < 3.5:
        return "medium"
    return "low"


def _note(sev):
    if sev == "critical":
        return "Критически низкая вовлечённость"
    if sev == "medium":
        return "Вовлечённость ниже нормы"
    return "В пределах нормы"


def department_breakdown(run, responses=None, city=None, job_title=None):
    """[{department, n, eng, enps, sev, note}] с гейтом N>=5."""
    survey = run.survey
    scale_ids = set(_scale_question_ids(survey, nps=False))
    nps_ids = set(_scale_question_ids(survey, nps=True))
    responses = list(responses if responses is not None else run.responses.all())
    by_dept = defaultdict(list)
    for r in responses:
        by_dept[r.department or "—"].append(r)

    out = []
    for dept, rs in by_dept.items():
        n = len(rs)
        if n < MIN_SEGMENT:
            out.append({"department": dept, "n": n, "suppressed": True})
            continue
        rid = [r.id for r in rs]
        eng = engagement(Answer.objects.filter(response_id__in=rid, question_id__in=scale_ids))
        nps_vals = list(Answer.objects.filter(response_id__in=rid, question_id__in=nps_ids)
                        .values_list("value_num", flat=True))
        sev = severity_for(eng)
        out.append({
            "department": dept, "n": n, "suppressed": False,
            "eng": eng, "enps": enps_from([v for v in nps_vals if v is not None]),
            "part": participation_pct(run, dept, city=city, job_title=job_title),
            "sev": sev, "note": _note(sev),
        })
    return sorted(out, key=lambda d: (d.get("eng") is None, d.get("eng") or 0))


def _week_label(dt):
    return dt.strftime("%d.%m")


def trend_series(run, responses=None):
    """Тренд вовлечённости по неделям ВНУТРИ волны: overall + по отделам."""
    scale_ids = set(_scale_question_ids(run.survey, nps=False))
    responses = list(responses if responses is not None else run.responses.all())
    responses = sorted(responses, key=lambda r: r.submitted_at)
    buckets = {}
    for r in responses:
        key = r.submitted_at.isocalendar()[:2]  # (year, week)
        buckets.setdefault(key, {"label": _week_label(r.submitted_at), "resp": []})
        buckets[key]["resp"].append(r)
    keys = sorted(buckets)
    labels = [buckets[k]["label"] for k in keys]

    def avg_for(rs):
        return engagement(Answer.objects.filter(response_id__in=[r.id for r in rs],
                                                 question_id__in=scale_ids))

    overall = [avg_for(buckets[k]["resp"]) for k in keys]

    depts = sorted({r.department or "—" for r in responses})
    dept_series = []
    for dept in depts:
        vals = []
        for k in keys:
            rs = [r for r in buckets[k]["resp"] if (r.department or "—") == dept]
            vals.append(avg_for(rs) if rs else None)
        dept_series.append({"department": dept, "values": vals})
    return {"labels": labels, "overall": overall, "departments": dept_series}


def audience_employees(survey):
    """Целевая аудитория опроса (учёт ролей и отделов из настроек опроса)."""
    roles = survey.audience_roles or [Employee.EMPLOYEE]
    target = Employee.objects.filter(role__in=roles)
    if survey.audience_departments:
        target = target.filter(department__in=survey.audience_departments)
    return target


def participation_pct(run, department=None, city=None, job_title=None):
    """% прохождения волны = прошедшие / целевая аудитория. None если базы нет."""
    target = audience_employees(run.survey)
    target = _seg(target, "department", department)
    target = _seg(target, "city", city)
    target = _seg(target, "job_title", job_title)
    total = target.count()
    if not total:
        return None
    done = Participation.objects.filter(run=run, employee__in=target).count()
    return round(done / total * 100)


def distribution(run, responses=None):
    """Распределение ответов по вариантам для single/multi вопросов."""
    rids = None if responses is None else [r.id for r in responses]
    out = []
    for q in run.survey.questions.filter(qtype__in=[Question.SINGLE, Question.MULTI]):
        answers = Answer.objects.filter(question=q, response__run=run)
        if rids is not None:
            answers = answers.filter(response_id__in=rids)
        counts = defaultdict(int)
        for a in answers:
            picks = a.value_json if isinstance(a.value_json, list) else [a.value_json]
            for p in picks:
                if p is not None:
                    counts[str(p)] += 1
        out.append({"question": q.text, "options": dict(counts)})
    return out


def by_day(run, responses=None):
    """График прохождений по дням (по submitted_at ответов — совпадает с прохождением)."""
    responses = responses if responses is not None else run.responses.all()
    counts = defaultdict(int)
    for r in responses:
        counts[r.submitted_at.date().isoformat()] += 1
    return [{"date": d, "count": counts[d]} for d in sorted(counts)]


def comments(run, limit=50, responses=None):
    """Текстовые комментарии (без привязки к личности в анонимном режиме)."""
    qs = Answer.objects.filter(response__run=run, value_text__isnull=False)
    if responses is not None:
        qs = qs.filter(response_id__in=[r.id for r in responses])
    qs = qs.exclude(value_text="").order_by("-id")[:limit]
    return [a.value_text for a in qs]


def overall_stats(run, responses=None, department=None, city=None, job_title=None):
    survey = run.survey
    scale_ids = set(_scale_question_ids(survey, nps=False))
    nps_ids = set(_scale_question_ids(survey, nps=True))
    base = responses if responses is not None else run.responses.all()
    rids = [r.id for r in base]
    eng = engagement(Answer.objects.filter(response_id__in=rids, question_id__in=scale_ids))
    nps_vals = list(Answer.objects.filter(response_id__in=rids, question_id__in=nps_ids)
                    .values_list("value_num", flat=True))
    return {
        "engagement": eng,
        "enps": enps_from([v for v in nps_vals if v is not None]),
        "participation": participation_pct(run, department=department, city=city, job_title=job_title),
        "responses": len(rids),
    }


# ── Сравнение волн (ТЗ: история запусков, сравнение во времени) ──────────────

def run_kpis(run):
    """Краткие KPI волны для сравнения серий: {label, engagement, enps, participation, responses}."""
    o = overall_stats(run)
    return {
        "run_id": run.id, "index": run.index,
        "label": run.title, "status": run.status,
        "ended_at": run.ends_at.isoformat() if run.ends_at else None,
        **o,
    }


def series_comparison(survey):
    """Сравнение волн опроса: KPI по волнам + матрица вовлечённости по отделам × волнам.

    Возвращает {runs:[run_kpis...], departments:[{department, values:[eng|None по волнам]}]}.
    Гейт N>=5 на сегмент сохраняется (отдел с n<5 в волне → None).
    """
    runs = list(survey.runs.exclude(status="draft").order_by("index"))
    runs = [r for r in runs if r.responses.exists()]
    run_cards = [run_kpis(r) for r in runs]

    # отделы по вовлечённости в каждой волне (с гейтом)
    dept_names = set()
    per_run_dept = []
    for r in runs:
        bd = {d["department"]: d for d in department_breakdown(r)}
        per_run_dept.append(bd)
        dept_names.update(bd.keys())
    departments = []
    for dept in sorted(dept_names):
        values = []
        for bd in per_run_dept:
            d = bd.get(dept)
            values.append(None if (d is None or d.get("suppressed")) else d.get("eng"))
        departments.append({"department": dept, "values": values})

    return {
        "survey": {"id": survey.id, "title": survey.title},
        "labels": [c["label"] for c in run_cards],
        "runs": run_cards,
        "departments": departments,
    }
