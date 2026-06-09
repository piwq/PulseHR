from rest_framework import serializers

from .models import Question, Survey


class QuestionSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = Question
        fields = ["id", "text", "qtype", "required", "order", "config", "branch_rules"]


class SurveySerializer(serializers.ModelSerializer):
    """Read + write (nested questions). Ветвление в branch_rules ссылается на вопрос по `order`."""

    questions = QuestionSerializer(many=True)
    response_count = serializers.SerializerMethodField()
    run_count = serializers.SerializerMethodField()
    runs = serializers.SerializerMethodField()

    class Meta:
        model = Survey
        fields = [
            "id", "title", "description", "mode", "status", "critical",
            "starts_at", "ends_at", "audience_roles", "audience_departments",
            "created_at", "questions", "response_count", "run_count", "runs",
        ]
        read_only_fields = ["created_at"]

    def get_response_count(self, obj):
        return obj.participations.count()

    def get_run_count(self, obj):
        return obj.runs.count()

    def get_runs(self, obj):
        return [
            {"id": r.id, "index": r.index, "label": r.title, "status": r.status,
             "ends_at": r.ends_at.isoformat() if r.ends_at else None,
             "responses": r.responses.count()}
            for r in obj.runs.order_by("index")
        ]

    def create(self, validated_data):
        questions = validated_data.pop("questions", [])
        survey = Survey.objects.create(**validated_data)
        self._sync_questions(survey, questions)
        return survey

    def update(self, instance, validated_data):
        questions = validated_data.pop("questions", None)
        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()
        if questions is not None:
            instance.questions.all().delete()  # builder перезаписывает вопросы целиком
            self._sync_questions(instance, questions)
        return instance

    @staticmethod
    def _sync_questions(survey, questions):
        for i, q in enumerate(questions):
            q.pop("id", None)
            q.setdefault("order", i + 1)
            Question.objects.create(survey=survey, **q)
