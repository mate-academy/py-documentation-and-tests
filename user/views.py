from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.settings import api_settings

from user.serializers import UserSerializer, AuthTokenSerializer


class CreateUserView(generics.CreateAPIView):
    serializer_class = UserSerializer

    def post(self, request, *args, **kwargs):
        """Create a user account."""
        return super().post(request, *args, **kwargs)


class CreateTokenView(ObtainAuthToken):
    renderer_classes = api_settings.DEFAULT_RENDERER_CLASSES
    serializer_class = AuthTokenSerializer

    def post(self, request, *args, **kwargs):
        """Login to your user account."""
        return super().post(request, *args, **kwargs)


class ManageUserView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user

    def get(self, request, *args, **kwargs):
        """Get user info."""
        return super().get(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        """Update user info."""
        return super().put(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        """Partial update user info."""
        return super().patch(request, *args, **kwargs)
