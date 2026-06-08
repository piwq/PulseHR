from django.contrib import admin

from .models import (ChannelPrefs, NotificationJob, NotificationLog,
                     PushSubscription, TelegramLink)


@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("id", "employee", "active", "user_agent", "last_seen")
    list_filter = ("active",)


@admin.register(TelegramLink)
class TelegramLinkAdmin(admin.ModelAdmin):
    list_display = ("employee", "chat_id", "linked_at")


@admin.register(ChannelPrefs)
class ChannelPrefsAdmin(admin.ModelAdmin):
    list_display = ("employee", "web_push", "sms", "telegram", "email", "preferred_time", "dnd_until")


@admin.register(NotificationJob)
class NotificationJobAdmin(admin.ModelAdmin):
    list_display = ("id", "survey", "employee", "trigger", "stage", "status", "next_attempt_at", "attempt")
    list_filter = ("status", "stage", "trigger")


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ("id", "survey", "employee", "channel", "status", "cost", "created_at")
    list_filter = ("channel", "status")
