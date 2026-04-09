from drf_yasg import openapi

from cinema.serializers import MovieListSerializer

title_param = openapi.Parameter(
    "title",
    openapi.IN_QUERY,
    description="Filter by title IDs. Provide a single title name",
    type=openapi.TYPE_STRING,
)

genres_param = openapi.Parameter(
    "genres",
    openapi.IN_QUERY,
    description="Filter by actor IDs. Provide a single ID or a comma-separated list of IDs (e.g., '1,2,5')",
    type=openapi.TYPE_STRING,
)

actors_param = openapi.Parameter(
    "actors",
    openapi.IN_QUERY,
    description="Filter by actor IDs. Provide a single ID or a comma-separated list of IDs (e.g., '1,2,5')",
    type=openapi.TYPE_STRING,
)

user_response = openapi.Response("response description", MovieListSerializer)
test_param = [title_param, genres_param, actors_param]
