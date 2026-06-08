import json
import logging

from django.conf import settings

from . import Result

log = logging.getLogger("notifications")


def send(employee, payload):
    """Отправка Web Push на все активные устройства; чистка мёртвых endpoint-ов."""
    if not settings.VAPID_PRIVATE_KEY:
        return Result(False, "VAPID не настроен", 0)
    try:
        from pywebpush import WebPushException, webpush
    except Exception:  # noqa: BLE001
        return Result(False, "pywebpush не установлен", 0)

    subs = list(employee.push_subscriptions.filter(active=True))
    if not subs:
        return Result(False, "нет push-подписок", 0)

    sent = 0
    for s in subs:
        try:
            webpush(
                subscription_info={"endpoint": s.endpoint, "keys": {"p256dh": s.p256dh, "auth": s.auth}},
                data=json.dumps(payload),
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={"sub": settings.VAPID_CLAIMS_SUB},
            )
            sent += 1
        except WebPushException as e:  # noqa: PERF203
            code = getattr(getattr(e, "response", None), "status_code", None)
            if code in (404, 410):
                s.active = False
                s.save(update_fields=["active"])
            log.warning("webpush fail %s: %s", s.endpoint[:40], code)
    return Result(sent > 0, f"{sent} устройств", 0)
