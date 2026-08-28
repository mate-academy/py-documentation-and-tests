from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

from user.serializers import UserSerializer


@extend_schema_view(
    post=extend_schema(
        summary="Create new user by email", request=UserSerializer
    ),
)
class CreateUserView(generics.CreateAPIView):
    serializer_class = UserSerializer


@extend_schema_view(
    get=extend_schema(
        summary="Retrieve user's info",
        request=UserSerializer,
    ),
    put=extend_schema(
        summary="Update existing user",
        request=UserSerializer,
    ),
    patch=extend_schema(
        summary="Update existing user partially",
        request=UserSerializer,
    ),
)
class ManageUserView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user


@extend_schema_view(
    post=extend_schema(
        summary="Obtain token by given credentials",
        request=api_settings.TOKEN_OBTAIN_SERIALIZER,
    ),
)
class CustomTokenObtainPairView(TokenObtainPairView):
    pass


@extend_schema_view(
    post=extend_schema(
        summary="Refresh token by given refresh token",
        request=api_settings.TOKEN_REFRESH_SERIALIZER,
    ),
)
class CustomTokenRefreshView(TokenRefreshView):
    pass


@extend_schema_view(
    post=extend_schema(
        summary="Verify is token valid",
        request=api_settings.TOKEN_REFRESH_SERIALIZER,
    ),
)
class CustomTokenVerifyView(TokenVerifyView):
    pass
