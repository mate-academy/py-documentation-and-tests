from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    extend_schema_view,
    extend_schema,
    OpenApiResponse,
    OpenApiExample
)
from rest_framework import generics
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.permissions import IsAuthenticated
from rest_framework.settings import api_settings

from user.serializers import AuthTokenSerializer
from user.serializers import UserSerializer


class CreateUserView(generics.CreateAPIView):
    """
    API view to create a new user.
    """
    serializer_class = UserSerializer


@extend_schema_view(
    post=extend_schema(
        summary="Obtain authentication token.",
        request=AuthTokenSerializer,
        tags=["User"],
        responses={
            200: OpenApiResponse(
                response={
                    "type": "object",
                    "properties": {
                        "token": {
                            "type": "string",
                            "example": "b93f81e76bded29c30ccf02bddeeaa8450c68",
                        }
                    },
                },
                description="Token obtained successfully.",
            ),
            400: OpenApiResponse(
                response={
                    "type": "object",
                    "properties": {
                        "non_field_errors": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "example": "Unable to log in with provided "
                                           "credentials.",
                            },
                        }
                    },
                },
                description="Invalid credentials provided.",
            ),
        },
    )
)
class CreateTokenView(ObtainAuthToken):
    """
    API view to obtain authentication token.
    Uses the custom AuthTokenSerializer.
    """
    renderer_classes = api_settings.DEFAULT_RENDERER_CLASSES
    serializer_class = AuthTokenSerializer


@extend_schema_view(
    get=extend_schema(
        summary="Retrieve User Information",
        description="Retrieve the authenticated user's information.",
        tags=["User"],
        responses={
            200: UserSerializer,
            401: OpenApiTypes.OBJECT,
        },
        examples=[
            OpenApiExample(
                "Successful response",
                summary="A successful response example",
                value={
                    "id": 1,
                    "email": "user@example.com",
                    "is_staff": False
                }
            ),
            OpenApiExample(
                "Unauthorized response",
                summary="An unauthorized response example",
                value={
                    "detail": "Authentication credentials were not provided."
                }
            )
        ]
    ),
    put=extend_schema(
        summary="Update User Information",
        description="Update the authenticated user's information.",
        tags=["User"],
        request=UserSerializer,
        responses={
            200: UserSerializer,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
        },
        examples=[
            OpenApiExample(
                "Successful response",
                summary="A successful response example",
                value={
                    "id": 1,
                    "email": "updated_user@example.com",
                    "is_staff": False
                }
            ),
            OpenApiExample(
                "Bad request response",
                summary="A bad request response example",
                value={
                    "email": ["This field is required."]
                }
            ),
            OpenApiExample(
                "Unauthorized response",
                summary="An unauthorized response example",
                value={
                    "detail": "Authentication credentials were not provided."
                }
            )
        ]
    ),
    patch=extend_schema(
        summary="Partially Update User Information",
        description="Partially update the authenticated user's information.",
        tags=["User"],
        request=UserSerializer,
        responses={
            200: UserSerializer,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
        },
        examples=[
            OpenApiExample(
                "Successful response",
                summary="A successful response example",
                value={
                    "id": 1,
                    "email": "partially_updated_user@example.com",
                    "is_staff": False
                }
            ),
            OpenApiExample(
                "Bad request response",
                summary="A bad request response example",
                value={
                    "email": ["This field is required."]
                }
            ),
            OpenApiExample(
                "Unauthorized response",
                summary="An unauthorized response example",
                value={
                    "detail": "Authentication credentials were not provided."
                }
            )
        ]
    )
)
class ManageUserView(generics.RetrieveUpdateAPIView):
    """
    API view for managing user information.
    """
    serializer_class = UserSerializer
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        """
        Get the authenticated user.
        """
        return self.request.user
