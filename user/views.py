from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from user.serializers import UserSerializer


class CreateUserView(generics.CreateAPIView):
    serializer_class = UserSerializer

    @extend_schema(
        summary="Create user",
        description="Creates a new user account",
        request=UserSerializer,
        responses={
            201: UserSerializer,
            400: OpenApiResponse(description="Validation error"),
        },
        tags=["Auth"],
    )
    def post(self, request, *args, **kwargs):
        """Creates user"""
        return super().post(request, *args, **kwargs)


class ManageUserView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="User profile",
        description="Returns user profile",
        responses={
            200: UserSerializer,
            401: OpenApiResponse(description="Unauthorized")
        },
        tags=["user"],
    )
    def get(self, request, *args, **kwargs):
        """Returns user profile"""
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Update user",
        description="Updates user profile",
        request=UserSerializer,
        responses={
            201: UserSerializer,
            401: OpenApiResponse(description="Unauthorized")
        },
        tags=["user"],
    )
    def put(self, request, *args, **kwargs):
        """Update user"""
        return super().put(request, *args, **kwargs)

    @extend_schema(
        summary="Partially update user",
        description="Partially updates user profile",
        request=UserSerializer,
        responses={
            201: UserSerializer,
            401: OpenApiResponse(description="Unauthorized")
        },
        tags=["user"],
    )
    def patch(self, request, *args, **kwargs):
        """Partially update user"""
        return super().patch(request, *args, **kwargs)

    def get_object(self):
        return self.request.user
