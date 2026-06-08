from django.urls import path

from . import views

urlpatterns = [
    path("request-code", views.request_code),
    path("verify", views.verify),
    path("me", views.me),
    path("consent", views.consent),
    path("departments", views.departments),
    path("employees", views.employees_list),
    path("employees/<int:pk>", views.employee_update),
]
