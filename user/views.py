from rest_framework import generics
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.settings import api_settings

from drf_spectacular.utils import extend_schema, OpenApiParameter

from user.serializers import UserSerializer, AuthTokenSerializer


class CreateUserView(generics.CreateAPIView):
    serializer_class = UserSerializer

    def post(self, request, *args, **kwargs):
        """endpoint for creating a new user"""
        return super().post(request, *args, **kwargs)


class ManageUserView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user

    def get(self, request, *args, **kwargs):
        """endpoint for retrieving an existing user"""
        return super().retrieve(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        """endpoint for updating an existing user"""
        return super().update(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        """endpoint for patching an existing user"""
        return super().patch(request, *args, **kwargs)
