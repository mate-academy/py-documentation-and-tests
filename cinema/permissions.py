from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAdminOrIfAuthenticatedReadOnly(BasePermission):
    """
    Custom permission for MovieViewSet and similar views.

    - Authenticated users can read
    (GET, HEAD, OPTIONS) but not write.
    - Admin users (is_staff) can read and write
    (POST, PUT, PATCH, DELETE).
    - Anonymous users have no access
    (cannot read or write).
    """
    def has_permission(self, request, view):
        return bool(
            (
                request.method in SAFE_METHODS
                and request.user
                and request.user.is_authenticated
            )
            or (request.user and request.user.is_staff)
        )


class AllowAnySafeMethodsOrAuthenticated(BasePermission):
    """
    Permission:

    - Anyone (authenticated or not)
    can perform safe methods: GET, HEAD, OPTIONS.
    - Authenticated users can perform unsafe methods:
    POST, PUT, PATCH, DELETE.
    """
    def has_permission(self, request, view):
        if request.method in ["GET", "HEAD", "OPTIONS"]:
            return True
        if request.user.is_authenticated:
            return True
        return False
