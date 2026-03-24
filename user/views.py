from drf_spectacular.utils import extend_schema, OpenApiExample
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from user.models import User
from user.serializers import UserSerializer


@extend_schema(
    summary="Register a new user",
    description="Creates a new user account with email and password",
    request=UserSerializer,
    responses={201: UserSerializer},
    examples=[
        OpenApiExample(
            "Example request",
            value={
                "email": "user@example.com",
                "password": "password123"
            },
            request_only=True,
        )
    ]
)
class CreateUserView(generics.CreateAPIView):
    serializer_class = UserSerializer


@extend_schema(
    methods=["GET"],
    summary="Retrieve current user profile",
    responses={200: UserSerializer}
)
@extend_schema(
    methods=["PUT"],
    summary="Update current user profile",
    responses={200: UserSerializer}
)
@extend_schema(
    methods=["PATCH"],
    summary="Partially update current user profile",
    responses={200: UserSerializer})
class ManageUserView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self) -> User:
        return self.request.user
