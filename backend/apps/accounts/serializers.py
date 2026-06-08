from rest_framework import serializers

from .models import Employee


class EmployeeSerializer(serializers.ModelSerializer):
    is_hr = serializers.BooleanField(read_only=True)
    consent_active = serializers.BooleanField(read_only=True)
    telegram_linked = serializers.SerializerMethodField()

    def get_telegram_linked(self, obj):
        return hasattr(obj, 'telegram') and obj.telegram is not None

    class Meta:
        model = Employee
        fields = ["id", "phone", "name", "department", "city", "role", "is_hr",
                  "consent_active", "consent_at", "consent_revoked_at", "telegram_linked"]
