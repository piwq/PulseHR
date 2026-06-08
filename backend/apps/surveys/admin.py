from django.contrib import admin
from django.utils import timezone

from .models import Answer, Participation, Question, Response, Survey


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 2
    fields = ("order", "qtype", "text", "required", "config", "branch_rules")


class DeletedFilter(admin.SimpleListFilter):
    title = "состояние"
    parameter_name = "deleted"

    def lookups(self, request, model_admin):
        return [("active", "Активные"), ("deleted", "Удалённые")]

    def queryset(self, request, queryset):
        if self.value() == "deleted":
            return queryset.filter(deleted_at__isnull=False)
        if self.value() == "active":
            return queryset.filter(deleted_at__isnull=True)
        return queryset


@admin.register(Survey)
class SurveyAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "mode", "status", "critical", "deleted_at", "created_at")
    list_filter = (DeletedFilter, "mode", "status", "critical")
    search_fields = ("title",)
    inlines = [QuestionInline]
    actions = ["restore_surveys", "soft_delete_surveys"]

    @admin.action(description="Восстановить выбранные опросы")
    def restore_surveys(self, request, queryset):
        n = queryset.update(deleted_at=None)
        self.message_user(request, f"Восстановлено опросов: {n}")

    @admin.action(description="Мягко удалить выбранные опросы")
    def soft_delete_surveys(self, request, queryset):
        n = queryset.update(deleted_at=timezone.now())
        self.message_user(request, f"Удалено (мягко): {n}")


class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 0


@admin.register(Response)
class ResponseAdmin(admin.ModelAdmin):
    list_display = ("id", "survey", "employee", "department", "completed", "submitted_at")
    list_filter = ("survey", "department", "completed")
    inlines = [AnswerInline]


@admin.register(Participation)
class ParticipationAdmin(admin.ModelAdmin):
    list_display = ("id", "survey", "employee", "completed_at")
    list_filter = ("survey",)
