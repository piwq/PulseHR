from django.db import models

from apps.surveys.models import Survey


class Insight(models.Model):
    survey = models.ForeignKey(Survey, related_name="insights", on_delete=models.CASCADE)
    department = models.CharField(max_length=120, blank=True)
    summary = models.TextField()
    # 1 — инфо, 2 — внимание, 3 — критично. [уточнить по ТЗ: severity-правила]
    severity = models.PositiveSmallIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    tg_sent = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Insight #{self.pk} sev={self.severity} ({self.department or '—'})"


class SurveyReport(models.Model):
    """ИИ-отчёт по опросу. Каждая генерация — новая версия (история сохраняется)."""

    survey = models.ForeignKey(Survey, related_name="ai_reports", on_delete=models.CASCADE)
    # {overall: str, problem_zones: [str], survey_quality: str, recommendations: [str]}
    content = models.JSONField()
    # Снимок метрик на момент генерации — для сравнения версий.
    kpis = models.JSONField(default=dict)
    model_used = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"SurveyReport survey={self.survey_id} ({self.model_used or '—'})"
