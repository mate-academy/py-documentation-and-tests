from drf_spectacular.utils import (
    extend_schema_view,
    extend_schema,
    OpenApiExample
)
from rest_framework import status
from user.serializers import UserSerializer

user_create_schema = extend_schema_view(
    post=extend_schema(
        description="Register a new user",
        request=UserSerializer,
        responses={
            status.HTTP_201_CREATED: UserSerializer,
            status.HTTP_400_BAD_REQUEST: "Bad Request"
        },
        examples=[
            OpenApiExample(
                name="CreateUserRequest",
                description="An example request to create a user",
                value={
                    "email": "example@example.com",
                    "password": "password123"
                },
                request_only=True
            ),
            OpenApiExample(
                name="CreateUserResponse",
                description="An example response after creating a user",
                value={
                    "id": 1,
                    "email": "example@example.com",
                    "is_staff": False
                },
                response_only=True
            )
        ]
    )
)

user_manage_schema = extend_schema_view(
    get=extend_schema(
        description="Get user data",
        responses={
            status.HTTP_200_OK: UserSerializer,
            status.HTTP_404_NOT_FOUND: "User not found",
        },
        examples=[
            OpenApiExample(
                name="GetUserResponse",
                description="An example response to get user data",
                value={
                    "id": 1,
                    "email": "example@example.com",
                    "is_staff": False,
                },
                response_only=True,
            )
        ]
    ),
    put=extend_schema(
        description="Update user data",
        request=UserSerializer,
        responses={
            status.HTTP_200_OK: UserSerializer,
            status.HTTP_400_BAD_REQUEST: "Bad Request",
            status.HTTP_404_NOT_FOUND: "User not found",
        },
        examples=[
            OpenApiExample(
                name="UpdateUserRequest",
                description="An example request to update user data",
                value={
                    "email": "updated@example.com",
                    "password": "newpassword123",
                },
                request_only=True,
            ),
            OpenApiExample(
                name="UpdateUserResponse",
                description="An example response after updating user data",
                value={
                    "id": 1,
                    "email": "updated@example.com",
                    "is_staff": False,
                },
                response_only=True,
            )
        ]
    ),
    patch=extend_schema(
        description="Partially update user data",
        request=UserSerializer,
        responses={
            status.HTTP_200_OK: UserSerializer,
            status.HTTP_400_BAD_REQUEST: "Bad Request",
            status.HTTP_404_NOT_FOUND: "User not found",
        },
        examples=[
            OpenApiExample(
                name="PartiallyUpdateUserRequest",
                description="An example request to partially update user data",
                value={
                    "email": "partialupdate@example.com",
                },
                request_only=True,
            ),
            OpenApiExample(
                name="PartiallyUpdateUserResponse",
                description="An example response after "
                            "partially updating user data",
                value={
                    "id": 1,
                    "email": "partialupdate@example.com",
                    "is_staff": False,
                },
                response_only=True,
            )
        ]
    )
)
