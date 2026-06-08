from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # Порядок важен: специфичные префиксы перехватываются до общего /api/.
    path("api/auth/", include("apps.accounts.urls")),
    path("api/insights/", include("apps.insights.urls")),
    path("api/notifications/", include("apps.notifications.urls")),
    path("api/", include("apps.surveys.urls")),
]
