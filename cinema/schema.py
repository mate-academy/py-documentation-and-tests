from drf_spectacular.utils import OpenApiParameter

movie_query_params = [
    OpenApiParameter(
        name="title",
        type=str,
        location=OpenApiParameter.QUERY,
        description="Filter movies by title",
    ),
    OpenApiParameter(
        name="genres",
        type=str,
        location=OpenApiParameter.QUERY,
        description="Filter movies by genres (comma-separated)",
    ),
    OpenApiParameter(
        name="actors",
        type=str,
        location=OpenApiParameter.QUERY,
        description="Filter movies by actors (comma-separated)",
    ),
]

movie_session_query_params = [
    OpenApiParameter(
        name="date",
        type=str,
        location=OpenApiParameter.QUERY,
        description="Filter movie sessions by date (YYYY-MM-DD)",
    ),
    OpenApiParameter(
        name="movie",
        type=int,
        location=OpenApiParameter.QUERY,
        description="Filter movie sessions by movie ID",
    ),
]
