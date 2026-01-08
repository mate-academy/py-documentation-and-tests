from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from rest_framework_simplejwt.authentication import JWTAuthentication
from drf_spectacular.utils import extend_schema, OpenApiParameter

from user.serializers import UserSerializer, MyTokenObtainPairSerializer


class CreateUserView(generics.CreateAPIView):
    """
    API view to create a new user in the system.
    Anyone can register a new user.
    """
    serializer_class = UserSerializer


@extend_schema(
    description="Obtain JWT token pair (access and refresh) for authentication"
)
class CreateTokenView(TokenObtainPairView):
    """
    API view to obtain JWT access and refresh tokens.
    """
    serializer_class = MyTokenObtainPairSerializer


@extend_schema(
    description="Refresh JWT access token using a valid refresh token"
)
class RefreshTokenView(TokenRefreshView):
    """
    API view to refresh JWT access token.
    """
    pass


class ManageUserView(generics.RetrieveUpdateAPIView):
    """
    API view to retrieve or update the authenticated user's profile.
    Requires JWT authentication.
    """
    serializer_class = UserSerializer
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        """Return the currently authenticated user"""
        return self.request.user
