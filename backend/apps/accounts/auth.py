from rest_framework import authentication, exceptions, permissions

from .models import AuthToken


class TokenAuthentication(authentication.BaseAuthentication):
    """Заголовок `Authorization: Token <key>` → request.user = Employee."""

    keyword = "Token"

    def authenticate(self, request):
        header = authentication.get_authorization_header(request).decode()
        if not header.startswith(self.keyword + " "):
            return None
        key = header[len(self.keyword) + 1:].strip()
        try:
            token = AuthToken.objects.select_related("employee").get(key=key)
        except AuthToken.DoesNotExist:
            raise exceptions.AuthenticationFailed("Недействительный токен")
        return (token.employee, token)


class IsHR(permissions.BasePermission):
    """Доступ только роли HR/Администратор."""

    message = "Требуется роль HR."

    def has_permission(self, request, view):
        return bool(getattr(request.user, "is_hr", False))
