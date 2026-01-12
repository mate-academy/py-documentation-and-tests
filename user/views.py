from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from user.serializers import UserSerializer


class CreateUserView(generics.CreateAPIView):
    serializer_class = UserSerializer


@extend_schema_view(
    get=extend_schema(
        description="Get the details of the currently authenticated user."
    ),
    put=extend_schema(
        description="Update all fields for the currently authenticated user."
    ),
    patch=extend_schema(
        description=(
            "Partially update the details of the currently authenticated user."
        )
    ),
)
class ManageUserView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user
