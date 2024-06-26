from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAdminOrIfAuthenticatedReadOnly(BasePermission):
    """
    Custom permission class that allows read-only access to authenticated users
    and full access to admin users.
    """

    def has_permission(self, request, view):
        """
        Check if the request user has permission to access the view.

        Args:
            request: Request object
            view: View object

        Returns:
            bool: True if the request user has permission, False otherwise
        """
        return bool(
            (
                request.method in SAFE_METHODS
                and request.user
                and request.user.is_authenticated
            )
            or (request.user and request.user.is_staff)
        )
