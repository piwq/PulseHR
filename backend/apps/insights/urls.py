from django.urls import path

from . import views

urlpatterns = [
    path("analyze/", views.analyze),
    path("alerts/stream/", views.alerts_stream),
    path("recent/", views.recent_insights),
    path("report-surveys/", views.report_surveys),
    path("report/<int:survey_id>/", views.survey_report),
    path("report/<int:survey_id>/generate/", views.generate_survey_report),
    path("<int:survey_id>/", views.InsightList.as_view()),
]
