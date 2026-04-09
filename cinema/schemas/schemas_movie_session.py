from drf_yasg import openapi

from cinema.serializers import MovieSessionSerializer

movie_param = openapi.Parameter(
    "movie",
    openapi.IN_QUERY,
    description="Filter by date movie name",
    type=openapi.TYPE_STRING,
)

date_param = openapi.Parameter(
    "date",
    openapi.IN_QUERY,
    description="Filter by date",
    type=openapi.TYPE_STRING,
    format=openapi.FORMAT_DATE,
)

movie_session_user_response = openapi.Response(
    "response description", MovieSessionSerializer
)
movie_session_test_param = [movie_param, date_param]
