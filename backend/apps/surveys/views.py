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
from .models import Answer, Participation, Question, Response, Survey, SurveyRun
from .serializers import SurveySerializer

log = logging.getLogger("surveys")

BANNER = {
    Survey.ANONYMOUS: "Этот опрос анонимный. HR не увидит ваши ответы.",
    Survey.IDENTIFIED: "Ваши ответы будут видны HR с указанием вашего имени.",
}


def _filters(request):
    """Сегментные фильтры аналитики из query-параметров (ТЗ: отделы/города/должности).

    city/job_title — мультивыбор: повторяющиеся параметры (?city=A&city=B) или через запятую.
    """
    def multi(name):
        out = []
        for v in request.query_params.getlist(name):
            out += [x.strip() for x in v.split(",") if x.strip()]
        return out or None

    return {
        "department": (request.query_params.get("department") or "").strip() or None,
        "city": multi("city"),
        "job_title": multi("job_title"),
    }


# ── Волны (SurveyRun) ───────────────────────────────────────────────────────

def _run_meta(run):
    return {"id": run.id, "index": run.index, "label": run.title, "status": run.status,
            "starts_at": run.starts_at.isoformat() if run.starts_at else None,
            "ends_at": run.ends_at.isoformat() if run.ends_at else None,
            "responses": run.responses.count()}


def _runs_list(survey):
    return [_run_meta(r) for r in survey.runs.order_by("index")]


def _pick_run(survey, request, with_data=False):
    """Выбрать волну: ?run_id → она; иначе активная или последняя (с данными, если with_data)."""
    rid = request.query_params.get("run_id")
    if rid:
        return survey.runs.filter(pk=rid).first()
    if with_data:
        run = survey.active_run
        if run and run.responses.exists():
            return run
        return survey.runs.filter(responses__isnull=False).order_by("-index").distinct().first() \
            or survey.active_run or survey.latest_run
    return survey.active_run or survey.latest_run


def _previous_run(run):
    """Предыдущая волна с данными (для дельты «к прошлой волне»)."""
    return (run.survey.runs.filter(index__lt=run.index, responses__isnull=False)
            .order_by("-index").distinct().first())


def _delta_vs_prev(run, prev):
    if prev is None:
        return None
    cur, pr = analytics.overall_stats(run), analytics.overall_stats(prev)

    def d(a, b):
        return None if (a is None or b is None) else round(a - b, 2)

    return {
        "prev_run_id": prev.id, "prev_label": prev.title,
        "engagement": d(cur["engagement"], pr["engagement"]),
        "enps": d(cur["enps"], pr["enps"]),
        "participation": d(cur["participation"], pr["participation"]),
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

    def _launch_run(self, survey):
        """Запустить новую волну: создать SurveyRun(active) + поставить уведомления аудитории."""
        last = survey.runs.order_by("-index").first()
        idx = (last.index + 1) if last else 1
        now = timezone.now()
        run = SurveyRun.objects.create(
            survey=survey, index=idx, status=SurveyRun.ACTIVE,
            starts_at=survey.starts_at or now,
            ends_at=survey.ends_at or now + timezone.timedelta(days=14),
        )
        survey.status = Survey.ACTIVE
        survey.save(update_fields=["status"])
        try:
            from apps.notifications.services import enqueue_for_trigger
            enqueue_for_trigger(run, "publish")
        except Exception as e:  # noqa: BLE001
            log.warning("enqueue publish skipped: %s", e)
        return run

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        """Первый запуск опроса (создаёт волну 1)."""
        survey = self.get_object()
        if survey.active_run:
            return ApiResponse({"detail": "Уже есть активная волна — сначала завершите её"},
                               status=status.HTTP_409_CONFLICT)
        self._launch_run(survey)
        return ApiResponse(SurveySerializer(survey).data)

    @action(detail=True, methods=["post"], permission_classes=[IsHR])
    def relaunch(self, request, pk=None):
        """Перезапустить опрос новой волной — вся история прошлых волн сохраняется."""
        survey = self.get_object()
        if survey.active_run:
            return ApiResponse({"detail": "Уже есть активная волна — сначала завершите её"},
                               status=status.HTTP_409_CONFLICT)
        run = self._launch_run(survey)
        return ApiResponse({**SurveySerializer(survey).data, "run": _run_meta(run)}, status=201)

    @action(detail=True, methods=["post"], permission_classes=[IsHR])
    def complete(self, request, pk=None):
        survey = self.get_object()
        run = survey.active_run
        if run:
            run.status = SurveyRun.COMPLETED
            run.save(update_fields=["status"])
        survey.sync_status()
        return ApiResponse(SurveySerializer(survey).data)

    @action(detail=True, methods=["post"], permission_classes=[IsHR])
    def archive(self, request, pk=None):
        survey = self.get_object()
        latest = survey.latest_run
        if latest:
            latest.status = SurveyRun.ARCHIVE
            latest.save(update_fields=["status"])
        survey.status = Survey.ARCHIVE
        survey.save(update_fields=["status"])
        return ApiResponse(SurveySerializer(survey).data)

    @action(detail=True, methods=["get"])
    def take(self, request, pk=None):
        """Данные опроса для прохождения сотрудником (+ плашка режима, флаг повтора)."""
        survey = get_object_or_404(Survey, pk=pk, deleted_at__isnull=True)
        emp = request.user
        run = survey.active_run
        already = bool(run) and Participation.objects.filter(run=run, employee=emp).exists()
        data = SurveySerializer(survey).data
        data["banner"] = BANNER[survey.mode]
        data["already_participated"] = already
        data["run_active"] = run is not None
        return ApiResponse(data)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        """Сохранение ответов в активную волну. Анти-повтор — в рамках волны."""
        survey = get_object_or_404(Survey, pk=pk, deleted_at__isnull=True)
        emp = request.user
        run = survey.active_run
        if run is None:
            return ApiResponse({"detail": "Опрос сейчас не активен"}, status=status.HTTP_409_CONFLICT)
        if Participation.objects.filter(run=run, employee=emp).exists():
            return ApiResponse({"detail": "Опрос уже пройден"}, status=status.HTTP_409_CONFLICT)

        identified = survey.mode == Survey.IDENTIFIED
        response = Response.objects.create(
            run=run, survey=survey,
            employee=emp if identified else None,
            session_id="" if identified else secrets.token_hex(8),
            department=emp.department,
            city=emp.city,
            job_title=emp.job_title,
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
        Participation.objects.create(run=run, survey=survey, employee=emp)
        return ApiResponse({"response_id": response.id}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"], permission_classes=[IsHR])
    def participants(self, request, pk=None):
        """Кто прошёл волну (для напоминаний). В анонимном режиме — без привязки к ответам."""
        survey = get_object_or_404(Survey, pk=pk, deleted_at__isnull=True)
        run = _pick_run(survey, request)
        rows = Participation.objects.filter(run=run).select_related("employee") if run else []
        return ApiResponse([
            {"employee_id": p.employee_id, "name": p.employee.name or p.employee.phone,
             "department": p.employee.department, "completed_at": p.completed_at.isoformat()}
            for p in rows
        ])

    @action(detail=True, methods=["get"], permission_classes=[IsHR])
    def comparison(self, request, pk=None):
        """Сравнение волн опроса: KPI по волнам + вовлечённость по отделам × волнам (ТЗ: история)."""
        survey = get_object_or_404(Survey, pk=pk, deleted_at__isnull=True)
        return ApiResponse(analytics.series_comparison(survey))

    @action(detail=True, methods=["get"], permission_classes=[IsHR])
    def stats(self, request, pk=None):
        """Полная аналитика опроса (ТЗ: % прохождения, по отделам, eNPS, распределение, по дням).

        Фильтры (ТЗ): ?department=&city=&job_title= — сегментирование с сохранением гейта N>=5.
        """
        survey = get_object_or_404(Survey, pk=pk, deleted_at__isnull=True)
        run = _pick_run(survey, request, with_data=True)
        if run is None:
            return ApiResponse({"survey_id": survey.id, "run": None, "runs": _runs_list(survey)})
        f = _filters(request)
        rs = list(analytics.filtered_responses(run, **f))
        prev = _previous_run(run)
        return ApiResponse({
            "survey_id": survey.id,
            "run": _run_meta(run),
            "runs": _runs_list(survey),
            "filters": f,
            "filter_options": analytics.filter_values(run),
            "overall": analytics.overall_stats(run, rs, **f),
            "delta": _delta_vs_prev(run, prev),
            "departments": analytics.department_breakdown(run, rs, city=f["city"], job_title=f["job_title"]),
            "trend": analytics.trend_series(run, rs),
            "distribution": analytics.distribution(run, rs),
            "by_day": analytics.by_day(run, rs),
            "comments": analytics.comments(run, responses=rs),
        })

    @action(detail=False, methods=["get"], permission_classes=[IsHR])
    def dashboard(self, request):
        """Сводка дашборда HR. ?id=X — опрос; ?run_id=Y — волна (иначе активная/последняя с данными)."""
        all_surveys = Survey.objects.filter(deleted_at__isnull=True).order_by("-created_at")
        surveys_list = [
            {"id": s.id, "title": s.title, "status": s.status, "mode": s.mode,
             "response_count": s.responses.count(), "run_count": s.runs.count()}
            for s in all_surveys
        ]

        survey_id = request.query_params.get("id")
        if survey_id:
            survey = get_object_or_404(Survey, pk=survey_id, deleted_at__isnull=True)
        else:
            survey = max(all_surveys, key=lambda s: s.responses.count(), default=None)

        run = _pick_run(survey, request, with_data=True) if survey else None
        if run is None or not run.responses.exists():
            return ApiResponse({"survey": None, "surveys": surveys_list})

        f = _filters(request)
        rs = list(analytics.filtered_responses(run, **f))
        overall = analytics.overall_stats(run, rs, **f)
        delta = _delta_vs_prev(run, _previous_run(run))
        return ApiResponse({
            "survey": {"id": survey.id, "title": survey.title, "mode": survey.mode, "status": survey.status},
            "surveys": surveys_list,
            "run": _run_meta(run),
            "runs": _runs_list(survey),
            "filters": f,
            "filter_options": analytics.filter_values(run),
            # engagement_delta = дельта вовлечённости К ПРОШЛОЙ ВОЛНЕ (ТЗ: сравнение во времени)
            "kpis": {**overall, "engagement_delta": (delta or {}).get("engagement")},
            "delta": delta,
            "departments": analytics.department_breakdown(run, rs, city=f["city"], job_title=f["job_title"]),
            "trend": analytics.trend_series(run, rs),
            "by_day": analytics.by_day(run, rs),
            "distribution": analytics.distribution(run, rs),
            "comments": analytics.comments(run, limit=5, responses=rs),
        })

    @action(detail=True, methods=["get"], permission_classes=[IsHR])
    def export(self, request, pk=None):
        """Выгрузка результатов волны в CSV/XLSX. Анонимный режим — без колонки автора."""
        survey = get_object_or_404(Survey, pk=pk, deleted_at__isnull=True)
        run = _pick_run(survey, request, with_data=True)
        fmt = request.query_params.get("fmt", "csv")
        questions = list(survey.questions.all())
        identified = survey.mode == Survey.IDENTIFIED
        header = (["Сотрудник"] if identified else []) + ["Отдел"] + [q.text for q in questions]

        rows = []
        responses = run.responses.all().prefetch_related("answers") if run else []
        for r in responses:
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
    """Доступные сотруднику опросы: активная волна ∧ аудитория ∧ эта волна ещё не пройдена."""
    emp = request.user
    out = []
    for s in Survey.objects.filter(status=Survey.ACTIVE, deleted_at__isnull=True).order_by("-created_at"):
        run = s.active_run
        if run is None or not s.targets(emp):
            continue
        if Participation.objects.filter(run=run, employee=emp).exists():
            continue
        out.append({
            "id": s.id, "title": s.title, "description": s.description,
            "mode": s.mode, "ends_at": run.ends_at.isoformat() if run.ends_at else None,
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
        .select_related("survey", "run")
        .order_by("-completed_at")
    )
    out = []
    for p in parts:
        s = p.survey
        if s.deleted_at:
            continue
        out.append({
            "id": s.id, "title": s.title, "mode": s.mode, "wave": p.run.index,
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
