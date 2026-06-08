"""Аналитика опросов: вовлечённость, eNPS, разбивка по отделам, тренд, распределение,
по дням, комментарии. Гейт анонимности N>=5 защищает от деанонимизации сегментов."""
from collections import defaultdict
from statistics import mean

from apps.accounts.models import Employee

from .models import Answer, Participation, Question, Response

MIN_SEGMENT = 5  # гейт анонимности: агрегат по сегменту только при N>=5


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


def severity_for(eng, drop):
    if eng is None:
        return "low"
    if eng < 3.0 or (drop is not None and drop >= 0.6):
        return "critical"
    if eng < 3.5 or (drop is not None and drop >= 0.3):
        return "medium"
    return "low"


def _note(sev, drop):
    if sev == "critical":
        return "Падение вовлечённости — требует внимания"
    if sev == "medium":
        return "Ниже нормы"
    return "В пределах нормы"


def department_breakdown(survey):
    """[{department, n, eng, enps, sev, note}] с гейтом N>=5."""
    scale_ids = set(_scale_question_ids(survey, nps=False))
    nps_ids = set(_scale_question_ids(survey, nps=True))
    responses = list(survey.responses.all())
    by_dept = defaultdict(list)
    for r in responses:
        by_dept[r.department or "—"].append(r)

    trend = trend_series(survey)  # для оценки падения
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
        series = next((s for s in trend["departments"] if s["department"] == dept), None)
        drop = None
        if series and len([v for v in series["values"] if v is not None]) >= 2:
            vals = [v for v in series["values"] if v is not None]
            drop = round(vals[0] - vals[-1], 2)
        sev = severity_for(eng, drop)
        out.append({
            "department": dept, "n": n, "suppressed": False,
            "eng": eng, "enps": enps_from([v for v in nps_vals if v is not None]),
            "part": participation_pct(survey, dept), "sev": sev, "note": _note(sev, drop),
        })
    return sorted(out, key=lambda d: (d.get("eng") is None, d.get("eng") or 0))


def _week_label(dt):
    return dt.strftime("%d.%m")


def trend_series(survey):
    """Тренд вовлечённости по неделям: overall + по отделам. {labels, overall, departments}."""
    scale_ids = set(_scale_question_ids(survey, nps=False))
    responses = list(survey.responses.all().order_by("submitted_at"))
    # бакеты по ISO-неделе
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


def participation_pct(survey, department=None):
    """% прохождения = прошедшие / целевая аудитория (по ролям/отделам). None если базы нет."""
    target = Employee.objects.filter(role=Employee.EMPLOYEE)
    if survey.audience_departments:
        target = target.filter(department__in=survey.audience_departments)
    if department:
        target = target.filter(department=department)
    total = target.count()
    if not total:
        return None
    done = Participation.objects.filter(survey=survey, employee__in=target).count()
    return round(done / total * 100)


def distribution(survey):
    """Распределение ответов по вариантам для single/multi вопросов."""
    out = []
    for q in survey.questions.filter(qtype__in=[Question.SINGLE, Question.MULTI]):
        counts = defaultdict(int)
        for a in Answer.objects.filter(question=q):
            picks = a.value_json if isinstance(a.value_json, list) else [a.value_json]
            for p in picks:
                if p is not None:
                    counts[str(p)] += 1
        out.append({"question": q.text, "options": dict(counts)})
    return out


def by_day(survey):
    """График прохождений по дням."""
    counts = defaultdict(int)
    for p in survey.participations.all():
        counts[p.completed_at.date().isoformat()] += 1
    return [{"date": d, "count": counts[d]} for d in sorted(counts)]


def comments(survey, limit=50):
    """Текстовые комментарии (без привязки к личности в анонимном режиме)."""
    qs = (Answer.objects.filter(response__survey=survey, value_text__isnull=False)
          .exclude(value_text="").order_by("-id")[:limit])
    return [a.value_text for a in qs]


def overall_stats(survey):
    scale_ids = set(_scale_question_ids(survey, nps=False))
    nps_ids = set(_scale_question_ids(survey, nps=True))
    rids = list(survey.responses.values_list("id", flat=True))
    eng = engagement(Answer.objects.filter(response_id__in=rids, question_id__in=scale_ids))
    nps_vals = list(Answer.objects.filter(response_id__in=rids, question_id__in=nps_ids)
                    .values_list("value_num", flat=True))
    return {
        "engagement": eng,
        "enps": enps_from([v for v in nps_vals if v is not None]),
        "participation": participation_pct(survey),
        "responses": len(rids),
    }
