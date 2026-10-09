from drf_spectacular.utils import (
    extend_schema_view,
    extend_schema,
    OpenApiParameter,
)

from cinema.serializers import MovieImageSerializer

movie_docs = extend_schema_view(
    list=extend_schema(
        summary="List of movies",
        description="Retrieve a list of movies.",
        parameters=[
            OpenApiParameter(
                name="genres",
                type=int,
                many=True,
                description="Filter by genres ids. Example: ?genres=1,2,3",
            ),
            OpenApiParameter(
                name="actors",
                type=int,
                many=True,
                description="Filter by actors ids. Example: ?actors=1,2,3",
            ),
            OpenApiParameter(
                name="title",
                type=str,
                many=False,
                description="Filter by movie title. Example: ?title=string",
            ),
        ],
    ),
    upload_image=extend_schema(
        summary="Upload image",
        description="Upload a poster image for the movie.",
        request={"multipart/form-data": MovieImageSerializer},
    ),
)

movie_session_docs = extend_schema_view(
    list=extend_schema(
        summary="List of movie sessions",
        description="Retrieve a list of movie sessions.",
        parameters=[
            OpenApiParameter(
                name="movie",
                type=int,
                description="Filter by movie id. Example: ?movie=1",
            ),
            OpenApiParameter(
                name="date",
                type=str,
                description="Filter by date. Example: ?date=2026-10-09",
            ),
        ],
    ),
)
