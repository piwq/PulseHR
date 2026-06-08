from django.contrib import admin

from .models import Insight


@admin.register(Insight)
class InsightAdmin(admin.ModelAdmin):
    list_display = ("id", "survey", "department", "severity", "tg_sent", "created_at")
    list_filter = ("severity", "tg_sent", "department")
