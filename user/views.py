from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from user.schemas.user_schemas import (
    user_create_schema,
    user_manage_schema
)
from user.serializers import UserSerializer


@user_create_schema
class CreateUserView(generics.CreateAPIView):
    serializer_class = UserSerializer


@user_manage_schema
class ManageUserView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user
