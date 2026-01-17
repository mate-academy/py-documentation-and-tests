from rest_framework import generics
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.settings import api_settings

from rest_framework_simplejwt.views import TokenObtainPairView

from drf_spectacular.utils import extend_schema, extend_schema_view


from user.serializers import UserSerializer, AuthTokenSerializer


@extend_schema(
    summary="Register user",
    description=(
        "Create a new user account.\n\n"
        "Returns the created user data. Password is write-only."
    ),
)
class CreateUserView(generics.CreateAPIView):
    serializer_class = UserSerializer


@extend_schema(
    summary="Obtain auth token",
    description=(
        "Authenticate user and obtain authentication token.\n\n"
        "Use the returned token in the Authorization header:\n"
        "`Authorization: Bearer <token>`"
    ),
)
class CreateTokenView(TokenObtainPairView):
    pass


@extend_schema_view(
    retrieve=extend_schema(
        summary="Retrieve profile",
        description="Get profile of the currently authenticated user.",
    ),
    update=extend_schema(
        summary="Update profile",
        description=(
            "Update the authenticated user's profile.\n\n"
            "Password is optional when updating."
        ),
    ),
    partial_update=extend_schema(
        summary="Partially update profile",
        description=(
            "Partially update the authenticated user's profile.\n\n"
            "Password is optional."
        ),
    ),
)
class ManageUserView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user
