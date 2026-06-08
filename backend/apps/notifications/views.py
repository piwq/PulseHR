import os

from django.conf import settings
from django.core import signing
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response as ApiResponse

from apps.accounts.auth import IsHR
from apps.surveys.models import Survey

from .models import ChannelPrefs, NotificationJob, NotificationLog, PushSubscription

TG_LINK_SALT = "pulsehr.tglink"


@api_view(["GET"])
@permission_classes([AllowAny])
def vapid_public_key(request):
    return ApiResponse({"public_key": settings.VAPID_PUBLIC_KEY})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def push_subscribe(request):
    sub = request.data.get("subscription") or request.data
    keys = sub.get("keys", {})
    obj, _ = PushSubscription.objects.update_or_create(
        endpoint=sub["endpoint"],
        defaults={"employee": request.user, "p256dh": keys.get("p256dh", ""),
                  "auth": keys.get("auth", ""), "active": True,
                  "user_agent": request.META.get("HTTP_USER_AGENT", "")[:255]},
    )
    return ApiResponse({"id": obj.id}, status=201)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def push_unsubscribe(request):
    PushSubscription.objects.filter(
        employee=request.user, endpoint=request.data.get("endpoint", "")).delete()
    return ApiResponse({"ok": True})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def devices(request):
    rows = request.user.push_subscriptions.filter(active=True)
    return ApiResponse([
        {"id": s.id, "user_agent": s.user_agent, "last_seen": s.last_seen.isoformat()}
        for s in rows
    ])


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def device_delete(request, pk):
    request.user.push_subscriptions.filter(id=pk).delete()
    return ApiResponse(status=204)


PREF_FIELDS = ["web_push", "sms", "telegram", "email", "preferred_time", "dnd_until"]


@api_view(["GET", "PUT"])
@permission_classes([IsAuthenticated])
def prefs(request):
    obj, _ = ChannelPrefs.objects.get_or_create(employee=request.user)
    if request.method == "PUT":
        for f in PREF_FIELDS:
            if f in request.data:
                setattr(obj, f, request.data[f])
        obj.save()
    return ApiResponse({f: getattr(obj, f) for f in PREF_FIELDS})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def telegram_qr(request):
    """Deep-link для привязки Telegram. Бот (run_bot) принимает /start <code>."""
    code = signing.dumps(request.user.id, salt=TG_LINK_SALT)
    bot = os.environ.get("TELEGRAM_BOT_USERNAME", "your_bot").lstrip("@")
    return ApiResponse({"deep_link": f"https://t.me/{bot}?start={code}", "code": code})


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def telegram_unlink(request):
    """Отвязать Telegram от аккаунта."""
    from .models import TelegramLink
    TelegramLink.objects.filter(employee=request.user).delete()
    return ApiResponse({"ok": True})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def track(request):
    """Отметка прочтения/клика из Service Worker (CTR-метрика)."""
    survey_id = request.data.get("survey_id")
    channel = request.data.get("channel", "push")
    event = request.data.get("event", "opened")  # opened | clicked
    log = (NotificationLog.objects
           .filter(survey_id=survey_id, employee=request.user, channel=channel)
           .order_by("-created_at").first())
    if log:
        log.status = NotificationLog.CLICKED if event == "clicked" else NotificationLog.OPENED
        log.save(update_fields=["status"])
    return ApiResponse({"ok": True})


@api_view(["POST"])
@permission_classes([IsHR])
def send_alert(request):
    """HR: поставить каскадные уведомления для аудитории опроса в очередь диспетчера."""
    from django.utils import timezone
    from apps.accounts.models import Employee
    from apps.surveys.models import Participation

    survey = get_object_or_404(Survey, pk=request.data.get("survey_id"))
    department = (request.data.get("department") or "").strip()

    taken = set(Participation.objects.filter(survey=survey).values_list("employee_id", flat=True))
    now = timezone.now()
    today = now.strftime("%Y%m%d")

    qs = Employee.objects.filter(role=Employee.EMPLOYEE)
    if department:
        qs = qs.filter(department=department)

    queued = 0
    for emp in qs:
        if emp.id in taken:
            continue
        if not emp.consent_active:
            continue
        # Не создаём если уже есть активное задание — но если предыдущее завершено, шлём снова
        active_exists = NotificationJob.objects.filter(
            survey=survey, employee=emp, trigger="manual", status=NotificationJob.ACTIVE,
        ).exists()
        if active_exists:
            continue
        dedup = f"{survey.id}:{emp.id}:manual:{now.strftime('%Y%m%d%H%M%S')}"
        NotificationJob.objects.create(
            survey=survey, employee=emp, trigger="manual",
            stage=NotificationJob.PUSH, next_attempt_at=now,
            dedup_key=dedup,
        )
        queued += 1

    return ApiResponse({
        "queued": queued,
        "survey_title": survey.title,
        "department": department or None,
    }, status=201 if queued else 200)


@api_view(["GET"])
@permission_classes([IsHR])
def delivery(request, survey_id):
    """Метрики каналов по опросу: отправлено/открыто/CTR/стоимость SMS."""
    survey = get_object_or_404(Survey, pk=survey_id)
    out = []
    for ch in ["push", "telegram", "sms", "email"]:
        qs = NotificationLog.objects.filter(survey=survey, channel=ch)
        agg = qs.aggregate(
            sent=Count("id", filter=~Q(status__in=[NotificationLog.FAILED, NotificationLog.SKIPPED])),
            opened=Count("id", filter=Q(status__in=[NotificationLog.OPENED, NotificationLog.CLICKED])),
            clicked=Count("id", filter=Q(status=NotificationLog.CLICKED)),
            cost=Sum("cost"),
        )
        sent = agg["sent"] or 0
        out.append({
            "channel": ch, "sent": sent, "opened": agg["opened"] or 0,
            "clicked": agg["clicked"] or 0,
            "ctr": round((agg["clicked"] or 0) / sent * 100) if sent else 0,
            "cost": float(agg["cost"] or 0),
        })
    return ApiResponse({"survey_id": survey.id, "channels": out})
