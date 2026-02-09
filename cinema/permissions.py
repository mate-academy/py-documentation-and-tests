from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAdminOrIfAuthenticatedReadOnly(BasePermission):
    def has_permission(self, request, view):
        # Allow read-only access for everyone
        if request.method in SAFE_METHODS:
            return True

        return bool(request.user and request.user.is_staff)
