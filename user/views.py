from rest_framework import generics
from rest_framework.authentication import BasicAuthentication
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.settings import api_settings

from user.models import User
from user.serializers import UserSerializer, AuthTokenSerializer


class CreateUserView(generics.CreateAPIView):
    serializer_class = UserSerializer
    authentication_classes = (BasicAuthentication,)
    permission_classes = (AllowAny,)


class CreateTokenView(ObtainAuthToken):
    renderer_classes = api_settings.DEFAULT_RENDERER_CLASSES
    serializer_class = AuthTokenSerializer
    authentication_classes = (BasicAuthentication,)
    permission_classes = (AllowAny,)


class ManageUserView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self) -> User:
        return self.request.user
