import json
import os
import time

from django.db.models import Count
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response as ApiResponse

from apps.accounts.auth import IsHR
from apps.surveys import analytics
from apps.surveys.models import Answer, Question, Survey

from .llm import analyze_texts, generate_report
from .models import Insight, SurveyReport
from .serializers import InsightSerializer


def ai_report_min_responses():
    """Минимум ответов, при котором опрос допускается к ИИ-отчёту (env, по умолч. 10)."""
    try:
        return int(os.environ.get("AI_REPORT_MIN_RESPONSES", "10"))
    except ValueError:
        return 10


@api_view(["POST"])
def analyze(request):
    """Тянет текстовые ответы → LLM (stub+fallback) → пишет Insight.

    Тело: {"survey_id": int, "department": str?}
    Поток рабочий, доменка (промпт/severity) — заглушка в llm.py.
    """
    survey = get_object_or_404(Survey, pk=request.data.get("survey_id"))
    department = request.data.get("department") or ""

    texts_qs = Answer.objects.filter(
        response__survey=survey, value_text__isnull=False,
    ).exclude(value_text="")
    if department:
        texts_qs = texts_qs.filter(response__department=department)
    texts = list(texts_qs.values_list("value_text", flat=True))

    result = analyze_texts(texts)
    insight = Insight.objects.create(
        survey=survey,
        department=department,
        summary=result["summary"],
        severity=result["severity"],
    )
    return ApiResponse(InsightSerializer(insight).data, status=201)


class InsightList(generics.ListAPIView):
    serializer_class = InsightSerializer

    def get_queryset(self):
        return Insight.objects.filter(survey_id=self.kwargs["survey_id"])


@api_view(["GET"])
def recent_insights(request):
    """Последние инсайты по всем опросам — для дропдауна уведомлений HR."""
    qs = Insight.objects.all().order_by("-created_at")[:10]
    return ApiResponse(InsightSerializer(qs, many=True).data)


def alerts_stream(request):
    """SSE-стрим инсайтов severity >= 2 (РАБОЧЕЕ).

    Отдаёт ': connected' сразу + heartbeat'ы, чтобы прокси/клиент видели поток.
    Стримятся только инсайты, появившиеся ПОСЛЕ подключения (для тоста на демо).
    """
    def event_stream():
        yield ": connected\n\n"
        last_id = int(request.GET.get("since", 0))
        while True:
            new = Insight.objects.filter(id__gt=last_id, severity__gte=2).order_by("id")
            if new:
                for ins in new:
                    last_id = ins.id
                    payload = {
                        "id": ins.id,
                        "survey_id": ins.survey_id,
                        "department": ins.department,
                        "summary": ins.summary,
                        "severity": ins.severity,
                        "created_at": ins.created_at.isoformat(),
                    }
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            else:
                # heartbeat КАЖДУЮ тихую итерацию — иначе nginx рвёт молчащий стрим
                yield ": ping\n\n"
            time.sleep(2)

    resp = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    resp["Cache-Control"] = "no-cache"
    resp["X-Accel-Buffering"] = "no"  # дублирует proxy_buffering off на стороне Django
    return resp


# ── ИИ-отчёт по опросу ──────────────────────────────────────────────────────

def build_report_context(survey):
    """Собрать компактный контекст для LLM из готовой аналитики (анонимность — гейт N>=5)."""
    questions = list(survey.questions.all().order_by("order"))
    return {
        "survey": {
            "title": survey.title,
            "description": survey.description,
            "mode": survey.mode,
            "status": survey.status,
        },
        "questions": [
            {"text": q.text, "type": q.qtype, "nps": bool(q.config.get("nps"))}
            for q in questions
        ],
        "has_nps_question": any(
            q.qtype == Question.SCALE and q.config.get("nps") for q in questions
        ),
        "overall": analytics.overall_stats(survey),
        "departments": analytics.department_breakdown(survey),
        "trend": analytics.trend_series(survey),
        "distribution": analytics.distribution(survey),
        "comments": analytics.comments(survey, limit=30),
    }


def _report_payload(report):
    return {
        "id": report.id,
        "content": report.content,
        "kpis": report.kpis,
        "model_used": report.model_used,
        "created_at": report.created_at.isoformat(),
    }


@api_view(["GET"])
@permission_classes([IsHR])
def report_surveys(request):
    """Опросы, допущенные к ИИ-отчёту (ответов >= порога), + сам порог."""
    min_n = ai_report_min_responses()
    qs = (Survey.objects.filter(deleted_at__isnull=True)
          .annotate(rc=Count("responses")).filter(rc__gte=min_n).order_by("-created_at"))
    return ApiResponse({
        "min_responses": min_n,
        "surveys": [
            {"id": s.id, "title": s.title, "status": s.status, "mode": s.mode, "response_count": s.rc}
            for s in qs
        ],
    })


@api_view(["GET"])
@permission_classes([IsHR])
def survey_report(request, survey_id):
    """Все версии ИИ-отчёта по опросу (новые первыми)."""
    get_object_or_404(Survey, pk=survey_id, deleted_at__isnull=True)
    reports = SurveyReport.objects.filter(survey_id=survey_id)
    return ApiResponse({"reports": [_report_payload(r) for r in reports]})


@api_view(["POST"])
@permission_classes([IsHR])
def generate_survey_report(request, survey_id):
    """Сгенерировать новую версию ИИ-отчёта (история прошлых версий сохраняется)."""
    survey = get_object_or_404(Survey, pk=survey_id, deleted_at__isnull=True)
    min_n = ai_report_min_responses()
    if survey.responses.count() < min_n:
        return ApiResponse({"detail": f"Для ИИ-отчёта нужно ≥ {min_n} ответов"}, status=400)

    ctx = build_report_context(survey)
    content, model_used = generate_report(ctx)
    report = SurveyReport.objects.create(
        survey=survey, content=content, kpis=ctx["overall"], model_used=model_used,
    )
    return ApiResponse({"report": _report_payload(report)}, status=201)
