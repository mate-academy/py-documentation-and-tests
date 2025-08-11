from drf_spectacular.utils import extend_schema
from rest_framework import generics

from rest_framework.permissions import IsAuthenticated


from user.serializers import UserSerializer


@extend_schema(tags=["user"])
class CreateUserView(generics.CreateAPIView):
    serializer_class = UserSerializer


@extend_schema(tags=["user"])
class ManageUserView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user
