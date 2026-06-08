import csv
import logging
import secrets

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response as ApiResponse

from apps.accounts.auth import IsHR

from . import analytics
from .models import Answer, Participation, Question, Response, Survey
from .serializers import SurveySerializer

log = logging.getLogger("surveys")

BANNER = {
    Survey.ANONYMOUS: "Этот опрос анонимный. HR не увидит ваши ответы.",
    Survey.IDENTIFIED: "Ваши ответы будут видны HR с указанием вашего имени.",
}


class SurveyViewSet(viewsets.ModelViewSet):
    """HR-конструктор: CRUD опросов + публикация. Аналитика — в Фазе D (stats/export)."""

    queryset = Survey.objects.filter(deleted_at__isnull=True).order_by("-created_at")
    serializer_class = SurveySerializer

    def get_permissions(self):
        # Прохождение/получение для опроса — для любого авторизованного; управление — только HR.
        if self.action in ("take", "submit"):
            return [IsAuthenticated()]
        return [IsHR()]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_destroy(self, instance):
        # Мягкое удаление — восстановление возможно в Django admin в течение 30 дней.
        instance.deleted_at = timezone.now()
        instance.save(update_fields=["deleted_at"])

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        survey = self.get_object()
        survey.status = Survey.ACTIVE
        survey.is_active = True
        if not survey.starts_at:
            survey.starts_at = timezone.now()
        if not survey.ends_at:
            survey.ends_at = timezone.now() + timezone.timedelta(days=14)
        survey.save()
        # Поставить каскадные уведомления аудитории (подсистема — Фаза E).
        try:
            from apps.notifications.services import enqueue_for_trigger
            enqueue_for_trigger(survey, "publish")
        except Exception as e:  # noqa: BLE001
            log.warning("enqueue publish skipped: %s", e)
        return ApiResponse(SurveySerializer(survey).data)

    @action(detail=True, methods=["post"], permission_classes=[IsHR])
    def complete(self, request, pk=None):
        survey = self.get_object()
        survey.status = Survey.COMPLETED
        survey.save(update_fields=["status"])
        return ApiResponse(SurveySerializer(survey).data)

    @action(detail=True, methods=["post"], permission_classes=[IsHR])
    def archive(self, request, pk=None):
        survey = self.get_object()
        survey.status = Survey.ARCHIVE
        survey.save(update_fields=["status"])
        return ApiResponse(SurveySerializer(survey).data)

    @action(detail=True, methods=["get"])
    def take(self, request, pk=None):
        """Данные опроса для прохождения сотрудником (+ плашка режима, флаг повтора)."""
        survey = get_object_or_404(Survey, pk=pk, deleted_at__isnull=True)
        emp = request.user
        already = Participation.objects.filter(survey=survey, employee=emp).exists()
        data = SurveySerializer(survey).data
        data["banner"] = BANNER[survey.mode]
        data["already_participated"] = already
        return ApiResponse(data)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        """Сохранение ответов. Анонимно → без employee (session_id); идентиф. → с employee."""
        survey = get_object_or_404(Survey, pk=pk, deleted_at__isnull=True)
        emp = request.user

        if Participation.objects.filter(survey=survey, employee=emp).exists():
            return ApiResponse({"detail": "Опрос уже пройден"}, status=status.HTTP_409_CONFLICT)

        identified = survey.mode == Survey.IDENTIFIED
        response = Response.objects.create(
            survey=survey,
            employee=emp if identified else None,
            session_id="" if identified else secrets.token_hex(8),
            department=emp.department,
        )
        Answer.objects.bulk_create([
            Answer(
                response=response,
                question_id=a["question_id"],
                value_num=a.get("value_num"),
                value_text=a.get("value_text"),
                value_json=a.get("value_json"),
            )
            for a in request.data.get("answers", [])
        ])
        Participation.objects.create(survey=survey, employee=emp)
        return ApiResponse({"response_id": response.id}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"], permission_classes=[IsHR])
    def participants(self, request, pk=None):
        """Кто прошёл опрос (для напоминаний). В анонимном режиме — без привязки к ответам."""
        survey = get_object_or_404(Survey, pk=pk, deleted_at__isnull=True)
        rows = Participation.objects.filter(survey=survey).select_related("employee")
        return ApiResponse([
            {"employee_id": p.employee_id, "name": p.employee.name or p.employee.phone,
             "department": p.employee.department, "completed_at": p.completed_at.isoformat()}
            for p in rows
        ])

    @action(detail=True, methods=["get"], permission_classes=[IsHR])
    def stats(self, request, pk=None):
        """Полная аналитика опроса (ТЗ: % прохождения, по отделам, eNPS, распределение, по дням)."""
        survey = get_object_or_404(Survey, pk=pk, deleted_at__isnull=True)
        return ApiResponse({
            "survey_id": survey.id,
            "overall": analytics.overall_stats(survey),
            "departments": analytics.department_breakdown(survey),
            "trend": analytics.trend_series(survey),
            "distribution": analytics.distribution(survey),
            "by_day": analytics.by_day(survey),
            "comments": analytics.comments(survey),
        })

    @action(detail=False, methods=["get"], permission_classes=[IsHR])
    def dashboard(self, request):
        """Сводка для дашборда HR. ?id=X — конкретный опрос; без параметра — с наибольшим числом ответов."""
        all_surveys = Survey.objects.filter(deleted_at__isnull=True).order_by("-created_at")
        surveys_list = [
            {"id": s.id, "title": s.title, "status": s.status, "mode": s.mode, "response_count": s.responses.count()}
            for s in all_surveys
        ]

        survey_id = request.query_params.get("id")
        if survey_id:
            survey = get_object_or_404(Survey, pk=survey_id, deleted_at__isnull=True)
        else:
            survey = max(all_surveys, key=lambda s: s.responses.count(), default=None)

        if survey is None or survey.responses.count() == 0:
            return ApiResponse({"survey": None, "surveys": surveys_list})

        overall = analytics.overall_stats(survey)
        trend = analytics.trend_series(survey)
        eng_vals = [v for v in trend["overall"] if v is not None]
        delta = round(eng_vals[-1] - eng_vals[0], 1) if len(eng_vals) >= 2 else None
        return ApiResponse({
            "survey": {"id": survey.id, "title": survey.title, "mode": survey.mode, "status": survey.status},
            "surveys": surveys_list,
            "kpis": {**overall, "engagement_delta": delta},
            "departments": analytics.department_breakdown(survey),
            "trend": trend,
            "by_day": analytics.by_day(survey),
            "distribution": analytics.distribution(survey),
            "comments": analytics.comments(survey, limit=5),
        })

    @action(detail=True, methods=["get"], permission_classes=[IsHR])
    def export(self, request, pk=None):
        """Выгрузка результатов в CSV/XLSX. Анонимный режим — без колонки автора."""
        survey = get_object_or_404(Survey, pk=pk, deleted_at__isnull=True)
        fmt = request.query_params.get("fmt", "csv")
        questions = list(survey.questions.all())
        identified = survey.mode == Survey.IDENTIFIED
        header = (["Сотрудник"] if identified else []) + ["Отдел"] + [q.text for q in questions]

        rows = []
        for r in survey.responses.all().prefetch_related("answers"):
            amap = {a.question_id: a for a in r.answers.all()}
            cells = []
            if identified:
                cells.append(r.employee.name if r.employee else "—")
            cells.append(r.department or "—")
            for q in questions:
                a = amap.get(q.id)
                cells.append(_answer_cell(a))
            rows.append(cells)

        if fmt == "xlsx":
            return _xlsx_response(survey, header, rows)
        return _csv_response(survey, header, rows)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me_surveys(request):
    """Доступные сотруднику опросы: активные ∧ аудитория ∧ ещё не пройдены."""
    emp = request.user
    taken = set(Participation.objects.filter(employee=emp).values_list("survey_id", flat=True))
    out = []
    for s in Survey.objects.filter(status=Survey.ACTIVE, deleted_at__isnull=True).order_by("-created_at"):
        if s.id in taken or not s.targets(emp):
            continue
        out.append({
            "id": s.id, "title": s.title, "description": s.description,
            "mode": s.mode, "ends_at": s.ends_at.isoformat() if s.ends_at else None,
            "question_count": s.questions.count(),
        })
    return ApiResponse(out)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me_surveys_completed(request):
    """Пройденные сотрудником опросы (архивный раздел)."""
    emp = request.user
    parts = (
        Participation.objects.filter(employee=emp)
        .select_related("survey")
        .order_by("-completed_at")
    )
    out = []
    for p in parts:
        s = p.survey
        if s.deleted_at:
            continue
        out.append({
            "id": s.id, "title": s.title, "mode": s.mode,
            "question_count": s.questions.count(),
            "completed_at": p.completed_at.isoformat() if p.completed_at else None,
        })
    return ApiResponse(out)


def _answer_cell(answer):
    if answer is None:
        return ""
    if answer.value_text:
        return answer.value_text
    if answer.value_num is not None:
        return answer.value_num
    if answer.value_json is not None:
        return ", ".join(map(str, answer.value_json)) if isinstance(answer.value_json, list) \
            else str(answer.value_json)
    return ""


def _csv_response(survey, header, rows):
    resp = HttpResponse(content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="survey_{survey.id}.csv"'
    resp.write("﻿")  # BOM для Excel
    writer = csv.writer(resp)
    writer.writerow(header)
    writer.writerows(rows)
    return resp


def _xlsx_response(survey, header, rows):
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Результаты"
    ws.append(header)
    for row in rows:
        ws.append(row)
    resp = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    resp["Content-Disposition"] = f'attachment; filename="survey_{survey.id}.xlsx"'
    wb.save(resp)
    return resp
