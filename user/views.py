from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from user.serializers import UserSerializer


@extend_schema_view(
    post=extend_schema(
        summary="Register a new user",
        description="Register a new user by providing"
                    " a unique email address and a secure password.",
    )
)
class CreateUserView(generics.CreateAPIView):
    serializer_class = UserSerializer


@extend_schema_view(
    get=extend_schema(
        summary="Retrieve profile",
        description="Get account details for"
                    " the currently authenticated user (id, email, is_staff).",
    ),
    put=extend_schema(
        summary="Update profile",
        description="Fully update the current user's profile."
    ),
    patch=extend_schema(
        summary="Partially update profile",
        description="Update specific fields"
                    " (e.g., password or email)"
                    " of the current user's profile.",
    ),
)
class ManageUserView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user
