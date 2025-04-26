from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAdminOrIfAuthenticatedReadOnly(BasePermission):
    """
    Allows:
    - Only SAFE_METHODS (GET, HEAD, OPTIONS) for authenticated users
    - Full access (all methods) for staff users (admins)
    - Denies all access to unauthenticated users
    - unless explicitly allowed in specific views
    """

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return request.user and request.user.is_staff
