from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    extend_schema_view,
    extend_schema,
    OpenApiParameter,
)


movie_session_viewset_schema = extend_schema_view(
    list=extend_schema(
        description="Get a list of all movie sessions.",
        parameters=[
            OpenApiParameter(
                name="date",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description="Filter movie sessions by date. Example: 2018-01-01.",
                required=False,
            ),
            OpenApiParameter(
                name="movie",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter movie sessions by movie. Movie ID expected. "
                "Example: 1.",
                required=False,
            ),
        ],
    ),
    retrieve=extend_schema(
        description="Get detailed info about a specific movie session.",
    ),
    create=extend_schema(
        description="Add a new movie session.",
    ),
    update=extend_schema(
        description="Update a specific movie session.",
    ),
    partial_update=extend_schema(
        description="Update a specific movie session.",
    ),
    destroy=extend_schema(
        description="Delete a specific movie session.",
    ),
)
