from django.urls import path

from . import views

urlpatterns = [
    path("vapid-public-key", views.vapid_public_key),
    path("push/subscribe", views.push_subscribe),
    path("push/unsubscribe", views.push_unsubscribe),
    path("devices", views.devices),
    path("devices/<int:pk>", views.device_delete),
    path("prefs", views.prefs),
    path("telegram/qr", views.telegram_qr),
    path("telegram/unlink", views.telegram_unlink),
    path("track", views.track),
    path("delivery/<int:survey_id>", views.delivery),
    path("send-alert", views.send_alert),
]
