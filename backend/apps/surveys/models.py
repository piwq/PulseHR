from django.db import models

from apps.accounts.models import Employee


class Survey(models.Model):
    ANONYMOUS = "anonymous"
    IDENTIFIED = "identified"
    MODE_CHOICES = [(ANONYMOUS, "Анонимный"), (IDENTIFIED, "Идентифицированный")]

    DRAFT, ACTIVE, COMPLETED, ARCHIVE = "draft", "active", "completed", "archive"
    STATUS_CHOICES = [(DRAFT, "Черновик"), (ACTIVE, "Активный"),
                      (COMPLETED, "Завершён"), (ARCHIVE, "Архив")]

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    mode = models.CharField(max_length=12, choices=MODE_CHOICES, default=ANONYMOUS)
    # Зеркало статуса последней волны (для списка опросов/фронта). Источник истины — SurveyRun.status.
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=DRAFT)
    critical = models.BooleanField(default=False)  # обязательный (152-ФЗ/выходное интервью)

    # Плановое окно (дефолт для новой волны). Фактическое окно живёт в SurveyRun.
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)

    # Пустой список = вся компания. Иначе фильтр аудитории.
    audience_roles = models.JSONField(default=list, blank=True)
    audience_departments = models.JSONField(default=list, blank=True)

    created_by = models.ForeignKey(Employee, null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name="created_surveys")
    created_at = models.DateTimeField(auto_now_add=True)
    # мягкое удаление: восстановление в админке в течение 30 дней, потом авто-чистка.
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    def __str__(self):
        return self.title

    @property
    def is_deleted(self):
        return self.deleted_at is not None

    @property
    def active_run(self):
        return self.runs.filter(status=self.ACTIVE).order_by("-index").first()

    @property
    def latest_run(self):
        return self.runs.order_by("-index").first()

    def sync_status(self):
        """Подтянуть зеркало статуса из последней волны (DRAFT, если волн нет)."""
        latest = self.latest_run
        self.status = latest.status if latest else self.DRAFT
        self.save(update_fields=["status"])

    def targets(self, employee):
        """Подходит ли сотрудник под аудиторию опроса."""
        if self.audience_roles and employee.role not in self.audience_roles:
            return False
        if self.audience_departments and employee.department not in self.audience_departments:
            return False
        return True


class SurveyRun(models.Model):
    """Волна (запуск) опроса. Один Survey → N волн; ответы/участия/уведомления — per-run."""

    DRAFT, ACTIVE, COMPLETED, ARCHIVE = "draft", "active", "completed", "archive"
    STATUS_CHOICES = Survey.STATUS_CHOICES

    survey = models.ForeignKey(Survey, related_name="runs", on_delete=models.CASCADE)
    index = models.PositiveIntegerField()           # порядковый номер волны: 1, 2, 3…
    label = models.CharField(max_length=120, blank=True)  # напр. «Q2 2026» (опционально)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=ACTIVE)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["survey", "index"]
        unique_together = [("survey", "index")]

    def __str__(self):
        return f"{self.survey.title} · волна {self.index}"

    @property
    def title(self):
        return self.label or f"Волна {self.index}"


class Question(models.Model):
    SINGLE = "single"   # одиночный выбор
    MULTI = "multi"     # множественный выбор
    SCALE = "scale"     # шкала (NPS/eNPS) — config.nps=true для NPS 0–10
    TEXT = "text"       # текстовый ответ
    MATRIX = "matrix"   # матричный вопрос
    QTYPE_CHOICES = [(SINGLE, SINGLE), (MULTI, MULTI), (SCALE, SCALE), (TEXT, TEXT), (MATRIX, MATRIX)]

    survey = models.ForeignKey(Survey, related_name="questions", on_delete=models.CASCADE)
    text = models.CharField(max_length=500)
    qtype = models.CharField(max_length=10, choices=QTYPE_CHOICES, default=SCALE)
    required = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    # config: варианты (single/multi), {min,max,low,high,nps} (scale), {rows,cols} (matrix)
    config = models.JSONField(default=dict, blank=True)
    # branch_rules.show_if: {"question": <id>, "op": "eq|ne|lte|gte|in", "value": ...}
    branch_rules = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"[{self.qtype}] {self.text}"

    @property
    def is_nps(self):
        return self.qtype == self.SCALE and bool(self.config.get("nps"))


class Response(models.Model):
    """Заполнение опроса.

    Анонимный режим: employee=None, ответы привязаны к session_id (деанонимизация невозможна).
    Идентифицированный: employee задан, HR видит автора.
    """

    run = models.ForeignKey("SurveyRun", related_name="responses", on_delete=models.CASCADE)
    # Денормализация опроса на ответ (survey == run.survey) — удобство запросов/совместимость.
    survey = models.ForeignKey(Survey, related_name="responses", on_delete=models.CASCADE)
    employee = models.ForeignKey(Employee, null=True, blank=True,
                                 on_delete=models.SET_NULL, related_name="responses")
    session_id = models.CharField(max_length=64, blank=True)
    # Денормализация сегментов на сам ответ — чтобы фильтровать анонимные ответы
    # (Response не связан с Employee) по отделу/городу/должности.
    department = models.CharField(max_length=120, blank=True)
    city = models.CharField(max_length=120, blank=True)
    job_title = models.CharField(max_length=120, blank=True)
    completed = models.BooleanField(default=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Response #{self.pk} ({self.department or '—'})"


class Answer(models.Model):
    response = models.ForeignKey(Response, related_name="answers", on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    value_num = models.FloatField(null=True, blank=True)   # scale
    value_text = models.TextField(null=True, blank=True)   # text
    value_json = models.JSONField(null=True, blank=True)   # single/multi/matrix

    def __str__(self):
        return f"Answer to Q#{self.question_id}"


class Participation(models.Model):
    """Кто прошёл волну — для напоминаний и анти-повтора. Анти-повтор per-run: новую волну можно пройти снова."""

    run = models.ForeignKey("SurveyRun", related_name="participations", on_delete=models.CASCADE)
    survey = models.ForeignKey(Survey, related_name="participations", on_delete=models.CASCADE)
    employee = models.ForeignKey(Employee, related_name="participations", on_delete=models.CASCADE)
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("run", "employee")]
