"""Окончательно удаляет мягко-удалённые опросы старше 30 дней."""
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.surveys.models import Survey

RETENTION_DAYS = 30


class Command(BaseCommand):
    help = "Hard-delete опросов, мягко удалённых более 30 дней назад."

    def handle(self, *args, **options):
        cutoff = timezone.now() - timezone.timedelta(days=RETENTION_DAYS)
        qs = Survey.objects.filter(deleted_at__lt=cutoff)
        n = qs.count()
        qs.delete()
        self.stdout.write(f"Окончательно удалено опросов: {n}")
