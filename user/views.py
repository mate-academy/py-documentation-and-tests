from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.views import (
    TokenObtainPairView as RestTokenObtainPairView,
    TokenRefreshView as RestTokenRefreshView,
    TokenVerifyView as RestTokenVerifyView,
)

from user.serializers import UserSerializer


@extend_schema(tags=["User API"])
class CreateUserView(generics.CreateAPIView):
    serializer_class = UserSerializer


@extend_schema(tags=["User API"])
class ManageUserView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user


@extend_schema(tags=["Token API"])
class TokenObtainPairView(RestTokenObtainPairView):
    pass


@extend_schema(tags=["Token API"])
class TokenRefreshView(RestTokenRefreshView):
    pass


@extend_schema(tags=["Token API"])
class TokenVerifyView(RestTokenVerifyView):
    pass
