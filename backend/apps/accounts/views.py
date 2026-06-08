import logging
import os

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response as ApiResponse

from .auth import IsHR
from .models import AuthToken, Department, Employee, OtpCode
from .serializers import EmployeeSerializer

log = logging.getLogger("accounts")

# Телефоны, которым при создании выдаётся роль HR (демо). Остальные — сотрудники.
HR_PHONES = {p.strip() for p in os.environ.get("HR_PHONES", "").split(",") if p.strip()}


@api_view(["POST"])
@permission_classes([AllowAny])
def request_code(request):
    """Имитация отправки OTP: код возвращается в ответе и пишется в лог (MVP без SMS-провайдера)."""
    phone = (request.data.get("phone") or "").strip()
    if not phone:
        return ApiResponse({"detail": "Укажите номер телефона"}, status=400)
    otp = OtpCode.issue(phone)
    log.info("OTP для %s: %s (имитация SMS)", phone, otp.code)
    return ApiResponse({"phone": phone, "sent": True, "debug_code": otp.code})


@api_view(["POST"])
@permission_classes([AllowAny])
def verify(request):
    """Проверка кода → создаёт/находит Employee, выдаёт токен."""
    phone = (request.data.get("phone") or "").strip()
    code = (request.data.get("code") or "").strip()
    otp = (
        OtpCode.objects.filter(phone=phone, code=code, used=False)
        .order_by("-created_at").first()
    )
    if not otp or not otp.is_valid:
        return ApiResponse({"detail": "Неверный или просроченный код"}, status=400)
    otp.used = True
    otp.save(update_fields=["used"])

    employee, created = Employee.objects.get_or_create(
        phone=phone,
        defaults={"role": Employee.HR if phone in HR_PHONES else Employee.EMPLOYEE},
    )
    # Авто-согласие при первом входе (MVP/демо: согласие показывается в UI отдельно)
    if not employee.consent_active:
        employee.consent_at = timezone.now()
        employee.consent_revoked_at = None
        employee.save(update_fields=["consent_at", "consent_revoked_at"])
    token = AuthToken.issue(employee)
    return ApiResponse({
        "token": token.key,
        "employee": EmployeeSerializer(employee).data,
        "new_account": created,
    })


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def me(request):
    """GET — текущий профиль. PATCH — обновить имя / отдел / город."""
    emp = request.user
    if request.method == "PATCH":
        for field in ("name", "department", "city"):
            if field in request.data:
                setattr(emp, field, (request.data[field] or "").strip())
        emp.save(update_fields=["name", "department", "city"])
    return ApiResponse(EmployeeSerializer(emp).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def consent(request):
    """152-ФЗ: фиксация согласия (give) или отзыва (revoke) на коммуникации."""
    emp = request.user
    action = request.data.get("action", "give")
    if action == "revoke":
        emp.consent_revoked_at = timezone.now()
    else:
        emp.consent_at = timezone.now()
        emp.consent_revoked_at = None
    emp.save(update_fields=["consent_at", "consent_revoked_at"])
    return ApiResponse(EmployeeSerializer(emp).data)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def departments(request):
    """GET — список отделов (из Employee + явно созданных HR). POST (HR) — создать отдел."""
    if request.method == "POST":
        if not request.user.is_hr:
            return ApiResponse({"detail": "Требуется роль HR."}, status=403)
        name = (request.data.get("name") or "").strip()
        if not name:
            return ApiResponse({"detail": "Укажите название отдела"}, status=400)
        _, created = Department.objects.get_or_create(name=name)
        if not created:
            return ApiResponse({"detail": f"Отдел «{name}» уже существует"}, status=409)

    from_employees = set(
        Employee.objects.exclude(department="")
        .values_list("department", flat=True).distinct()
    )
    explicit = set(Department.objects.values_list("name", flat=True))
    return ApiResponse(sorted(from_employees | explicit))


@api_view(["GET", "POST"])
@permission_classes([IsHR])
def employees_list(request):
    """HR: список сотрудников (GET) или предварительная регистрация (POST)."""
    if request.method == "POST":
        phone = (request.data.get("phone") or "").strip()
        if not phone:
            return ApiResponse({"detail": "Укажите телефон"}, status=400)
        defaults = {
            "name": (request.data.get("name") or "").strip(),
            "department": (request.data.get("department") or "").strip(),
            "role": request.data.get("role", Employee.EMPLOYEE),
        }
        emp, created = Employee.objects.get_or_create(phone=phone, defaults=defaults)
        if not created:
            for field in ("name", "department"):
                v = (request.data.get(field) or "").strip()
                if v:
                    setattr(emp, field, v)
            emp.save(update_fields=["name", "department"])
        return ApiResponse(EmployeeSerializer(emp).data, status=201 if created else 200)

    qs = Employee.objects.all().order_by("department", "name", "phone")
    return ApiResponse(EmployeeSerializer(qs, many=True).data)


@api_view(["PATCH"])
@permission_classes([IsHR])
def employee_update(request, pk):
    """HR: обновить профиль сотрудника (имя, отдел, роль)."""
    emp = get_object_or_404(Employee, pk=pk)
    for field in ("name", "department", "city", "role"):
        if field in request.data:
            setattr(emp, field, (request.data[field] or "").strip() if field != "role" else request.data[field])
    emp.save(update_fields=["name", "department", "city", "role"])
    return ApiResponse(EmployeeSerializer(emp).data)
