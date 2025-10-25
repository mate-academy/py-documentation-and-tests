from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiResponse, OpenApiExample


SCHEMA_API_RESPONSE_401 = OpenApiResponse(
    response=OpenApiTypes.OBJECT,
    description="Unauthorized",
    examples=[
        OpenApiExample(
            value={"detail": "Authentication credentials were not provided."},
            name="Unauthorized",
            response_only=True,
        )
    ],
)


SCHEMA_API_RESPONSE_429 = OpenApiResponse(
    response=OpenApiTypes.OBJECT,
    description="Request was throttled",
    examples=[
        OpenApiExample(
            value={
                "detail": """
                Request was throttled. Expected available in {seconds} seconds.
                """
            },
            name="Request was throttled.",
            response_only=True,
        ),
    ]
)


SCHEMA_API_RESPONSE_403 = OpenApiResponse(
    response=OpenApiTypes.OBJECT,
    description="Forbidden",
    examples=[
        OpenApiExample(
            value={
                "detail": """
                You do not have permission to perform this action.
                """
            },
            name="Forbidden",
            response_only=True,
        )
    ]
)
