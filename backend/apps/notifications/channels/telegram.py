import logging
import os

import requests

from . import Result

log = logging.getLogger("notifications")
API = "https://api.telegram.org/bot{token}/sendMessage"


def send(employee, payload):
    """Telegram с inline-кнопкой «Пройти опрос». Требует привязки чата (deep-link)."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    link = getattr(employee, "telegram", None)
    if not token or link is None:
        return Result(False, "TG не привязан", 0)
    url = payload["url"]
    # localhost/127.0.0.1 отклоняются Telegram API — шлём без кнопки
    is_local = "localhost" in url or "127.0.0.1" in url
    body = {"chat_id": link.chat_id, "text": f"📋 {payload['title']}\n{payload['body']}"}
    if not is_local:
        body["reply_markup"] = {"inline_keyboard": [[{"text": "Пройти опрос", "url": url}]]}
    else:
        body["text"] += f"\n\n🔗 {url}"
    try:
        r = requests.post(API.format(token=token), timeout=10, json=body)
        data = r.json()
        if not data.get("ok"):
            log.warning("telegram API error: %s", data.get("description"))
            return Result(False, data.get("description", "tg error"), 0)
        return Result(True, "ok", 0)
    except Exception as e:  # noqa: BLE001
        log.warning("telegram send fail: %s", e)
        return Result(False, str(e), 0)
