from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from user.serializers import UserSerializer


@extend_schema(
    summary="Create user",
    description="Create a new user account.",
    request=UserSerializer,
    responses=UserSerializer,
)
class CreateUserView(generics.CreateAPIView):
    serializer_class = UserSerializer


@extend_schema(
    summary="Manage current user",
    description=(
        "Retrieve or update the profile of the currently "
        "authenticated user."
    ),
    request=UserSerializer,
    responses=UserSerializer,
)
class ManageUserView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user
