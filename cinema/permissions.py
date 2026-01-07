from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAdminOrIfAuthenticatedReadOnly(BasePermission):
    def has_permission(self, request, view):
        """Allow read-only access to everyone
           and write access only to staff."""
        return (
            (request.method in SAFE_METHODS)
            or (request.user and request.user.is_staff)
        )
