import logging

from . import Result

log = logging.getLogger("notifications")


def send(employee, payload):
    """Имитация e-mail-рассылки: логируется для метрик, реально не отправляется."""
    log.info("EMAIL→%s: %s (имитация)", employee.phone, payload["title"])
    return Result(True, "имитация e-mail", 0)
