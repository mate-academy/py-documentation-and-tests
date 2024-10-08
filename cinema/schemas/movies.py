from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    extend_schema_view,
    extend_schema,
    OpenApiParameter,
)


movie_viewset_schema = extend_schema_view(
    list=extend_schema(
        description="Get a list of all movies",
        parameters=[
            OpenApiParameter(
                name="title",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter movies by title. Case-insensitive."
                "Multiple values can be provided, separated by commas."
                "Example: Inception, The Unbreakable",
                required=False,
            ),
            OpenApiParameter(
                name="genres",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter movies by genres. Genre ID expected."
                "Multiple values can be provided, separated by commas."
                "Example: 1, 3.",
                required=False,
            ),
            OpenApiParameter(
                name="actors",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter movies by actors. Actor ID expected."
                "Multiple values can be provided, separated by commas."
                "Example: 1, 3",
                required=False,
            ),
        ],
    ),
    retrieve=extend_schema(
        description="Get detailed information about a specific movie.",
    ),
    create=extend_schema(
        description="Add a new movie.",
    ),
    upload_image=extend_schema(
        description="Upload an image for a specific movie.",
    )
)
