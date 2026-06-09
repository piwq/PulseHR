from django.db import models

from apps.accounts.models import Employee
from apps.surveys.models import Survey, SurveyRun


class PushSubscription(models.Model):
    """Web Push подписка устройства (мультидевайс на сотрудника)."""

    employee = models.ForeignKey(Employee, related_name="push_subscriptions", on_delete=models.CASCADE)
    endpoint = models.URLField(max_length=600, unique=True)
    p256dh = models.CharField(max_length=255)
    auth = models.CharField(max_length=255)
    user_agent = models.CharField(max_length=255, blank=True)
    active = models.BooleanField(default=True)
    last_seen = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"push:{self.employee_id}:{self.endpoint[:32]}"


class TelegramLink(models.Model):
    """Привязка Telegram через deep-link /start <token>."""

    employee = models.OneToOneField(Employee, related_name="telegram", on_delete=models.CASCADE)
    chat_id = models.CharField(max_length=64)
    linked_at = models.DateTimeField(auto_now_add=True)


class ChannelPrefs(models.Model):
    """Настройки каналов сотрудника + DND. Критичные опросы каскад доставляет независимо."""

    MORNING, DAY, EVENING, ANY = "morning", "day", "evening", "any"
    TIME_CHOICES = [(MORNING, "утром"), (DAY, "днём"), (EVENING, "вечером"), (ANY, "любое")]

    employee = models.OneToOneField(Employee, related_name="channel_prefs", on_delete=models.CASCADE)
    web_push = models.BooleanField(default=True)
    sms = models.BooleanField(default=True)
    telegram = models.BooleanField(default=True)
    email = models.BooleanField(default=True)
    preferred_time = models.CharField(max_length=10, choices=TIME_CHOICES, default=ANY)
    dnd_until = models.DateTimeField(null=True, blank=True)

    def channel_enabled(self, channel):
        return getattr(self, channel, True)


class NotificationJob(models.Model):
    """Каскадная задача: уведомить сотрудника об опросе. Диспетчер эскалирует по стадиям/таймерам."""

    PUSH, TELEGRAM, SMS, EMAIL, DONE = "push", "telegram", "sms", "email", "done"
    STAGE_ORDER = [PUSH, TELEGRAM, SMS, EMAIL, DONE]

    ACTIVE, COMPLETED, STOPPED = "active", "completed", "stopped"
    STATUS_CHOICES = [(ACTIVE, "active"), (COMPLETED, "completed"), (STOPPED, "stopped")]

    run = models.ForeignKey(SurveyRun, related_name="notif_jobs", on_delete=models.CASCADE)
    survey = models.ForeignKey(Survey, related_name="notif_jobs", on_delete=models.CASCADE)
    employee = models.ForeignKey(Employee, related_name="notif_jobs", on_delete=models.CASCADE)
    trigger = models.CharField(max_length=32)  # publish | reminder48 | reminder24 | pulse | added
    stage = models.CharField(max_length=10, default=PUSH)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=ACTIVE)
    critical = models.BooleanField(default=False)  # обязательные опросы (152-ФЗ, выходное интервью)
    next_attempt_at = models.DateTimeField()
    attempt = models.PositiveIntegerField(default=0)
    dedup_key = models.CharField(max_length=120, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["status", "next_attempt_at"])]


class NotificationLog(models.Model):
    """Журнал отправок: аудит, дедуп, дневной лимит, метрики каналов (CTR, стоимость SMS)."""

    SENT, DELIVERED, OPENED, CLICKED, FAILED, SKIPPED = (
        "sent", "delivered", "opened", "clicked", "failed", "skipped")
    STATUS_CHOICES = [(SENT, SENT), (DELIVERED, DELIVERED), (OPENED, OPENED),
                      (CLICKED, CLICKED), (FAILED, FAILED), (SKIPPED, SKIPPED)]

    employee = models.ForeignKey(Employee, related_name="notif_logs", on_delete=models.CASCADE)
    run = models.ForeignKey(SurveyRun, related_name="notif_logs", on_delete=models.CASCADE, null=True)
    survey = models.ForeignKey(Survey, related_name="notif_logs", on_delete=models.CASCADE)
    channel = models.CharField(max_length=10)  # push | telegram | sms | email
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=SENT)
    cost = models.DecimalField(max_digits=8, decimal_places=2, default=0)  # стоимость (SMS)
    detail = models.CharField(max_length=255, blank=True)
    dedup_key = models.CharField(max_length=140, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["employee", "created_at"])]
