import logging
from decimal import Decimal

from . import Result

log = logging.getLogger("notifications")
SMS_COST = Decimal("5.00")  # имитация стоимости отправки одного SMS


def send(employee, payload):
    """Имитация SMS-провайдера: реально не шлёт, но логирует статус и стоимость для метрик."""
    text = f"PulseHR: новый опрос «{payload['survey_title']}». Пройти: {payload['url']}"
    log.info("SMS→%s: %s (имитация, %s₽)", employee.phone, text, SMS_COST)
    return Result(True, "имитация SMS", SMS_COST)
