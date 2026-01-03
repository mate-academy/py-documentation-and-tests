import django_filters
from django_filters import rest_framework as filters

from cinema.models import (
    Movie,
    MovieSession,
)


class NumberInFilter(
    filters.BaseInFilter,
    filters.NumberFilter,
):
    """Allows ?genres=1,2,3 / ?actors=4,5"""


class MovieFilter(filters.FilterSet):
    title = filters.CharFilter(field_name="title", lookup_expr="icontains")
    genres = NumberInFilter(field_name="genres__id", lookup_expr="in")
    actors = NumberInFilter(field_name="actors__id", lookup_expr="in")

    class Meta:
        model = Movie
        fields = ("title", "genres", "actors")


class MovieSessionFilter(filters.FilterSet):
    date = filters.DateFilter(field_name="show_time", lookup_expr="date")
    movie = filters.NumberFilter(field_name="movie__id")

    class Meta:
        model = MovieSession
        fields = ("date", "movie")
