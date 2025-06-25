from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter

filter_date_param = OpenApiParameter(
    name="date",
    type=OpenApiTypes.DATE,
    location="query",
    description="Filter by date in YYYY-MM-DD format")

filter_movie_param = OpenApiParameter(
    name="movie",
    type=OpenApiTypes.INT,
    location="query",
    description="Filter by movies id (ex. ?movie=1,2", )

filter_actors_param = OpenApiParameter(
    name="actors",
    type=OpenApiTypes.INT,
    location="query",
    description="Filter by actors id (ex. ?actors=1,2")

filter_genres_param = OpenApiParameter(
    name="genres",
    type=OpenApiTypes.INT,
    location="query",
    description="Filter by genres id (ex. ?genres=1,2")
filter_title_param = OpenApiParameter(
    name="title",
    type=OpenApiTypes.STR,
    location="query",
    description="Filter by title`s name (case-insensitive, partial match)")
