from rest_framework import serializers

from .models import Insight


class InsightSerializer(serializers.ModelSerializer):
    class Meta:
        model = Insight
        fields = ["id", "survey", "department", "summary", "severity", "tg_sent", "created_at"]
