from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    extend_schema, OpenApiParameter, OpenApiExample
)


def movie_filter_schema():
    """
    Adds to Swagger documentation all
    query params (title, genres, actors)
    """
    return extend_schema(
        parameters=[
            OpenApiParameter(
                name="title",
                description="Filter movies by title",
                required=False,
                location=OpenApiParameter.QUERY,
                type=str,
                examples=[
                    OpenApiExample(
                        name="Example 1",
                        summary="Filter by title",
                        description="Filters and return results by part "
                                    "of title and return 'Looper' film",
                        value="looper"
                    ),
                    OpenApiExample(
                        name="Example 2",
                        summary="Filter by partial title "
                                "(any part of the title)",
                        description="Filters and return results by part of "
                                    "title and return 'Inception' film",
                        value="cept"
                    ),
                ],
            ),
            OpenApiParameter(
                name="genres",
                description="Filter movies by genre. You should know genre's "
                            "id. (Example: ?genres=1,7)",
                type={"type": "array", "items": {"type": "number"}},
                examples=[
                    OpenApiExample(
                        name="Example 1",
                        summary="Filter by genre id",
                        description="Filters and return movies which have "
                                    "genre.id = 5 (Adventure). "
                                    "Result - 'Inception'",
                        value=5
                    ),
                    OpenApiExample(
                        name="Example 2",
                        summary="Filter by few genres ids (id1 AND id2)",
                        description="Filters and return movies which have "
                                    "genre.id = 2 (Drama) AND  "
                                    "genre.id = 7 (Mystery). "
                                    "Result - 'Unbreakable'",
                        value=[1, 7]
                    ),
                    OpenApiExample(
                        name="Example 3",
                        summary="Filter by few genres ids (id1 OR id2)",
                        description="Filters and return movies which have "
                                    "genre.id = 1 (Crime) OR  "
                                    "genre.id = 7 (Mystery). "
                                    "Results - 'The Departed', 'Unbreakable'",
                        value="1,7"
                    ),
                ],
            ),
            OpenApiParameter(
                name="actors",
                description="Filter movies by actor(s). You should know "
                            "actors's id. (Example: ?actors=1,7)",
                type={"type": "array", "items": {"type": "number"}},
                examples=[
                    OpenApiExample(
                        name="Example 1",
                        summary="Filter by actor's id",
                        description="Filters and return movies with actor "
                                    "actor.id = 3 (Matt Damon). "
                                    "Result - 'The Departed'",
                        value=3
                    ),
                    OpenApiExample(
                        name="Example 2",
                        summary="Filter by few actors ids (id1 OR id2)",
                        description="Filters and return movies which have "
                                    "actor.id = 1 (Leonardo DiCaprio) OR  "
                                    "actor.id = 2 (Jack Nicholson). "
                                    "Results - 'The Departed'",
                        value=[1, 2]
                    ),
                ],
            ),
        ]
    )


def movie_session_filter_schema():
    """Adds to Swagger documentation all query params (date, movie)"""
    return extend_schema(
        parameters=[
            OpenApiParameter(
                name="date",
                description="Filter movie_sessions by date",
                required=False,
                location=OpenApiParameter.QUERY,
                type=OpenApiTypes.DATE,
                examples=[
                    OpenApiExample(
                        name="Example",
                        summary="Filter by date",
                        description="Filters and return results by date of "
                                    "movie_session. "
                                    "Result - 'movie_session #7'",
                        value="2024-10-14"
                    ),
                ],
            ),
            OpenApiParameter(
                name="movie",
                description="Filter movie_sessions by movie (id).",
                type={"type": "number"},
                examples=[
                    OpenApiExample(
                        name="Example",
                        summary="Filter by movie id",
                        description="Filters and return movie_sessions which "
                                    "have movie.id = 4 (Unbreakable). "
                                    "Result - 'movie_session #4', "
                                    "'movie_session #5'",
                        value=4
                    )
                ],
            ),
        ]
    )
