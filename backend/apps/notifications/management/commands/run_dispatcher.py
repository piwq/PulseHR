"""DB-воркер подсистемы уведомлений (замена Celery/Redis).

Каждую итерацию: создаёт напоминания по расписанию (48ч/24ч) и обрабатывает «созревшие»
каскадные задания. Не падает на ошибках отдельных заданий.
"""
import logging
import time

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.notifications import services

log = logging.getLogger("notifications")
POLL_SECONDS = 3


class Command(BaseCommand):
    help = "Каскадная рассылка уведомлений (поллинг БД, без брокера)."

    def handle(self, *args, **options):
        self.stdout.write("run_dispatcher: луп запущен")
        while True:
            try:
                now = timezone.now()
                services.run_scheduler(now)
                services.dispatch_due(now)
            except Exception as e:  # noqa: BLE001
                log.warning("dispatcher loop error: %s", e)
            time.sleep(POLL_SECONDS)
