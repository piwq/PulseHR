from django.contrib import admin

from .models import Employee, OtpCode


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("id", "phone", "name", "department", "city", "role", "consent_active")
    list_filter = ("role", "department")
    search_fields = ("phone", "name")


@admin.register(OtpCode)
class OtpCodeAdmin(admin.ModelAdmin):
    list_display = ("phone", "code", "used", "expires_at", "created_at")
    list_filter = ("used",)
