"""Генерация пары VAPID-ключей для Web Push. Вставьте вывод в .env."""
import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from django.core.management.base import BaseCommand


def _b64u(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


class Command(BaseCommand):
    help = "Сгенерировать VAPID_PUBLIC_KEY / VAPID_PRIVATE_KEY для Web Push."

    def handle(self, *args, **options):
        priv = ec.generate_private_key(ec.SECP256R1())
        raw_priv = priv.private_numbers().private_value.to_bytes(32, "big")
        pub = priv.public_key().public_bytes(
            serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
        self.stdout.write("VAPID_PRIVATE_KEY=" + _b64u(raw_priv))
        self.stdout.write("VAPID_PUBLIC_KEY=" + _b64u(pub))
