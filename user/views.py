from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.settings import api_settings

from user.serializers import UserSerializer, AuthTokenSerializer


@extend_schema(
    summary="Register a new user",
    description="Creates a new user by email and password. "
                "Available without authentication.",
)
class CreateUserView(generics.CreateAPIView):
    serializer_class = UserSerializer


@extend_schema(
    summary="Obtain an auth token",
    description="Returns the authentication token for the given email and "
                "password. Use it as 'Authorization: Token <your token>'.",
)
class CreateTokenView(ObtainAuthToken):
    renderer_classes = api_settings.DEFAULT_RENDERER_CLASSES
    serializer_class = AuthTokenSerializer


@extend_schema_view(
    get=extend_schema(
        summary="Retrieve own profile",
        description="Returns the profile of the current "
                    "authenticated user.",
    ),
    put=extend_schema(
        summary="Update own profile",
        description="Fully updates the profile of the current "
                    "authenticated user.",
    ),
    patch=extend_schema(
        summary="Partially update own profile",
        description="Updates the given fields of the profile of the "
                    "current authenticated user.",
    ),
)
class ManageUserView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user
