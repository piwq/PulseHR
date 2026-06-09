import secrets

from django.db import models
from django.utils import timezone


class Employee(models.Model):
    """Сотрудник = один номер телефона. Роль разделяет HR/админа и рядового сотрудника."""

    HR = "hr"
    EMPLOYEE = "employee"
    ROLE_CHOICES = [(HR, "HR / Администратор"), (EMPLOYEE, "Сотрудник")]

    phone = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=120, blank=True)
    department = models.CharField(max_length=120, blank=True)
    job_title = models.CharField(max_length=120, blank=True)
    city = models.CharField(max_length=120, blank=True)
    role = models.CharField(max_length=12, choices=ROLE_CHOICES, default=EMPLOYEE)

    # 152-ФЗ: согласие на коммуникации фиксируется при первом входе, отзыв — стоп рассылок.
    consent_at = models.DateTimeField(null=True, blank=True)
    consent_revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # DRF совместимость (Employee играет роль request.user)
    is_authenticated = True
    is_anonymous = False

    def __str__(self):
        return f"{self.name or self.phone} ({self.role})"

    @property
    def is_hr(self):
        return self.role == self.HR

    @property
    def consent_active(self):
        return self.consent_at is not None and self.consent_revoked_at is None


class Department(models.Model):
    """HR-управляемый список отделов. Дополняет отделы из профилей сотрудников."""

    name = models.CharField(max_length=120, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class OtpCode(models.Model):
    """Одноразовый код. В MVP «отправка SMS» имитируется: код возвращается в ответе и в логах."""

    phone = models.CharField(max_length=32, db_index=True)
    code = models.CharField(max_length=8)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    @classmethod
    def issue(cls, phone, ttl_seconds=300):
        code = f"{secrets.randbelow(1000000):06d}"
        return cls.objects.create(
            phone=phone, code=code,
            expires_at=timezone.now() + timezone.timedelta(seconds=ttl_seconds),
        )

    @property
    def is_valid(self):
        return not self.used and timezone.now() < self.expires_at


class AuthToken(models.Model):
    """Простая токен-сессия (DRF-style). Фронт хранит ключ и шлёт в заголовке Authorization."""

    key = models.CharField(max_length=64, unique=True)
    employee = models.ForeignKey(Employee, related_name="tokens", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    @classmethod
    def issue(cls, employee):
        return cls.objects.create(key=secrets.token_hex(24), employee=employee)
