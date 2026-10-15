from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
)
from rest_framework import generics
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated


from user.serializers import UserSerializer, AuthTokenSerializer


@extend_schema(
    summary="Register a new user",
    description="Creates a new user account. Available for anonymous users.",
)
class CreateUserView(generics.CreateAPIView):
    serializer_class = UserSerializer


@extend_schema_view(
    get=extend_schema(
        summary="Get current user",
        description="Returns the profile of the authenticated user.",
    ),
    put=extend_schema(
        summary="Update current user",
        description="Fully updates the authenticated user's profile.",
    ),
    patch=extend_schema(
        summary="Partially update current user",
        description="Partially updates the authenticated user's profile.",
    ),
)
class ManageUserView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user
