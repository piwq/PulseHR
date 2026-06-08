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
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=DRAFT)
    critical = models.BooleanField(default=False)  # обязательный (152-ФЗ/выходное интервью)

    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)

    # Пустой список = вся компания. Иначе фильтр аудитории.
    audience_roles = models.JSONField(default=list, blank=True)
    audience_departments = models.JSONField(default=list, blank=True)

    created_by = models.ForeignKey(Employee, null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name="created_surveys")
    created_at = models.DateTimeField(auto_now_add=True)
    # совместимость со старым фронтом/Фазой 0
    is_active = models.BooleanField(default=True)
    # мягкое удаление: восстановление в админке в течение 30 дней, потом авто-чистка.
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    def __str__(self):
        return self.title

    @property
    def is_deleted(self):
        return self.deleted_at is not None

    def targets(self, employee):
        """Подходит ли сотрудник под аудиторию опроса."""
        if self.audience_roles and employee.role not in self.audience_roles:
            return False
        if self.audience_departments and employee.department not in self.audience_departments:
            return False
        return True


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

    survey = models.ForeignKey(Survey, related_name="responses", on_delete=models.CASCADE)
    employee = models.ForeignKey(Employee, null=True, blank=True,
                                 on_delete=models.SET_NULL, related_name="responses")
    session_id = models.CharField(max_length=64, blank=True)
    department = models.CharField(max_length=120, blank=True)
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
    """Кто прошёл опрос — для напоминаний и анти-повтора. В анонимном режиме НЕ связана с ответами."""

    survey = models.ForeignKey(Survey, related_name="participations", on_delete=models.CASCADE)
    employee = models.ForeignKey(Employee, related_name="participations", on_delete=models.CASCADE)
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("survey", "employee")]
