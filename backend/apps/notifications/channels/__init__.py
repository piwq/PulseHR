"""Канал-адаптеры. Web Push и Telegram — живые; SMS и e-mail — имитация (логируются)."""
from collections import namedtuple

Result = namedtuple("Result", ["ok", "detail", "cost"])
