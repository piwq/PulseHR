"""Telegram-бот: outbound алерты + inbound привязка аккаунта по /start <code>.

Луп каждые ~3с: (1) Insight(severity>=2, tg_sent=False) → алерт руководителю;
(2) getUpdates → /start <code> → привязка TelegramLink к сотруднику (deep-link из кабинета).
Без токена — логирует и крутится вхолостую, НЕ падает.
"""
import logging
import os
import time

import requests
from django.core import signing
from django.core.management.base import BaseCommand

from apps.accounts.models import Employee
from apps.insights.models import Insight
from apps.notifications.models import TelegramLink

log = logging.getLogger("bot")

API = "https://api.telegram.org/bot{token}/{method}"
POLL_SECONDS = 3
TG_LINK_SALT = "pulsehr.tglink"


class Command(BaseCommand):
    help = "Поллит инсайты и шлёт алерты руководителю в Telegram (outbound-only)."

    def handle(self, *args, **options):
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        chat_id = os.environ.get("MANAGER_CHAT_ID", "").strip()

        if not token:
            log.warning("TELEGRAM_BOT_TOKEN не задан — бот в холостом режиме, не падает.")
        else:
            try:
                r = requests.get(API.format(token=token, method="getMe"), timeout=10)
                username = r.json().get("result", {}).get("username")
                log.info("Telegram подключён: @%s", username)
            except Exception as e:  # noqa: BLE001
                log.warning("getMe не удался (бот продолжит работу): %s", e)

        # chat_id → code ожидающих подтверждения переприязки
        self._pending = {}

        self.stdout.write("run_bot: луп запущен")
        offset = 0
        while True:
            try:
                for ins in Insight.objects.filter(severity__gte=2, tg_sent=False):
                    if token and chat_id:
                        self._send(token, chat_id, ins)
                        ins.tg_sent = True
                        ins.save(update_fields=["tg_sent"])
                if token:
                    offset = self._poll_links(token, offset)
            except Exception as e:  # noqa: BLE001
                log.warning("ошибка в лупе бота: %s", e)
            time.sleep(POLL_SECONDS)

    def _reply(self, token, chat_id, text):
        try:
            requests.post(API.format(token=token, method="sendMessage"),
                          json={"chat_id": chat_id, "text": text}, timeout=10)
        except Exception as e:  # noqa: BLE001
            log.warning("reply fail: %s", e)

    def _reply_confirm(self, token, chat_id, text):
        """Отправить сообщение с кнопками подтверждения переприязки."""
        try:
            requests.post(API.format(token=token, method="sendMessage"), timeout=10, json={
                "chat_id": chat_id,
                "text": text,
                "reply_markup": {"inline_keyboard": [[
                    {"text": "✅ Да, отвязать", "callback_data": "tglink_confirm"},
                    {"text": "❌ Отмена", "callback_data": "tglink_cancel"},
                ]]},
            })
        except Exception as e:  # noqa: BLE001
            log.warning("reply_confirm fail: %s", e)

    def _answer_cb(self, token, cb_id):
        try:
            requests.post(API.format(token=token, method="answerCallbackQuery"),
                          json={"callback_query_id": cb_id}, timeout=5)
        except Exception:  # noqa: BLE001
            pass

    def _apply_link(self, token, chat, code):
        """Применить привязку (используется и напрямую, и после подтверждения)."""
        try:
            emp_id = signing.loads(code, salt=TG_LINK_SALT, max_age=86400)
            emp = Employee.objects.get(id=emp_id)
        except signing.SignatureExpired:
            self._reply(token, chat, "Ссылка устарела. Сгенерируйте новую в приложении PulseHR.")
            return
        except Exception:  # noqa: BLE001
            self._reply(token, chat, "Ошибка привязки. Попробуйте снова через приложение.")
            return
        TelegramLink.objects.filter(chat_id=str(chat)).delete()
        TelegramLink.objects.update_or_create(employee=emp, defaults={"chat_id": str(chat)})
        self._reply(token, chat, "✅ Telegram привязан к PulseHR. Теперь вы будете получать опросы здесь.")
        log.info("TG привязан: employee=%s chat=%s", emp_id, chat)

    def _poll_links(self, token, offset):
        r = requests.get(API.format(token=token, method="getUpdates"),
                         params={"offset": offset, "timeout": 0}, timeout=15)
        for upd in r.json().get("result", []):
            offset = upd["update_id"] + 1

            # ── callback_query (нажатие inline-кнопки) ──────────────────────
            cb = upd.get("callback_query")
            if cb:
                cb_id = cb["id"]
                cb_chat = cb.get("message", {}).get("chat", {}).get("id")
                data = cb.get("data", "")
                self._answer_cb(token, cb_id)

                if data == "tglink_confirm":
                    code = self._pending.pop(cb_chat, None)
                    if code:
                        self._apply_link(token, cb_chat, code)
                    else:
                        self._reply(token, cb_chat, "Сессия истекла. Повторите привязку через приложение.")
                elif data == "tglink_cancel":
                    self._pending.pop(cb_chat, None)
                    self._reply(token, cb_chat, "Привязка отменена.")
                continue

            # ── обычное сообщение ────────────────────────────────────────────
            msg = upd.get("message") or {}
            text = (msg.get("text") or "").strip()
            chat = msg.get("chat", {}).get("id")
            if chat is None:
                continue

            if not text.startswith("/start"):
                self._reply(token, chat,
                            "Привет! Я бот PulseHR.\n"
                            "Чтобы привязать аккаунт, нажмите «Привязать» в приложении и перейдите по ссылке.")
                continue

            parts = text.split(" ", 1)
            if len(parts) < 2 or not parts[1].strip():
                self._reply(token, chat,
                            "Для привязки нужна ссылка из приложения PulseHR.\n"
                            "Откройте «Настройки уведомлений» → «Привязать» и перейдите по сгенерированной ссылке.")
                continue

            code = parts[1].strip()
            try:
                emp_id = signing.loads(code, salt=TG_LINK_SALT, max_age=86400)
                emp = Employee.objects.get(id=emp_id)
            except signing.SignatureExpired:
                self._reply(token, chat, "Ссылка устарела. Сгенерируйте новую в приложении PulseHR.")
                continue
            except Exception:  # noqa: BLE001
                self._reply(token, chat, "Неверная ссылка. Попробуйте снова через приложение PulseHR.")
                continue

            # Если этот chat уже привязан к ДРУГОМУ аккаунту — спросить подтверждение
            conflict = TelegramLink.objects.filter(chat_id=str(chat)).exclude(employee=emp).first()
            if conflict:
                self._pending[chat] = code
                self._reply_confirm(token, chat,
                    "⚠️ Этот Telegram уже привязан к другому аккаунту PulseHR.\n"
                    "Отвязать предыдущий и привязать к текущему?")
                continue

            self._apply_link(token, chat, code)
        return offset

    def _send(self, token, chat_id, ins):
        text = (
            "⚠️ PulseHR алерт\n"
            f"Отдел: {ins.department or '—'}\n"
            f"Severity: {ins.severity}\n"
            f"{ins.summary}"
        )
        requests.post(
            API.format(token=token, method="sendMessage"),
            json={"chat_id": chat_id, "text": text},
            timeout=10,
        )
