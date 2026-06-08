from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter(trailing_slash=True)
router.register("surveys", views.SurveyViewSet, basename="survey")

urlpatterns = [
    path("me/surveys/", views.me_surveys),
    path("me/surveys/completed/", views.me_surveys_completed),
    *router.urls,
]
