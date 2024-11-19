from rest_framework import generics
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.settings import api_settings

from user.serializers import UserSerializer, AuthTokenSerializer


class CreateUserView(generics.CreateAPIView):
    serializer_class = UserSerializer

    def post(self, request, *args, **kwargs):
        """Created a new user"""
        return self.create(request, *args, **kwargs)


class CreateTokenView(ObtainAuthToken):
    renderer_classes = api_settings.DEFAULT_RENDERER_CLASSES
    serializer_class = AuthTokenSerializer

    def post(self, request, *args, **kwargs):
        """Login endpoint"""
        return super().post(request, *args, **kwargs)


class ManageUserView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user

    def get(self, request, *args, **kwargs):
        """Retrieve information about current user"""
        return super().get(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        """Update all information about current users"""
        return super().get(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        """Update partial information about current users"""
        return super().partial_update(request, *args, **kwargs)
