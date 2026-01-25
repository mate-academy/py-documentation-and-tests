# cinema/views.py

from datetime import datetime

from django.db.models import F, Count
from rest_framework import viewsets, mixins, status
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ReadOnlyModelViewSet

from cinema.models import Genre, Actor, CinemaHall, Movie, MovieSession, Order
from cinema.permissions import IsAdminOrIfAuthenticatedReadOnly

from cinema.serializers import (
    GenreSerializer,
# ... (outros imports de serializadores)
)

from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample # NOVO IMPORT

# ... (outros ViewSets)

class MovieViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Movie.objects.prefetch_related("genres", "actors")
    serializer_class = MovieSerializer
    authentication_classes = (TokenAuthentication,) # TokenAuthentication ainda está aqui
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    @staticmethod
    def _params_to_ints(qs):
        """Converts a list of string IDs to a list of integers"""
        return [int(str_id) for str_id in qs.split(",")]

    def get_queryset(self):
        """Retrieve the movies with filters"""
        title = self.request.query_params.get("title")
        genres = self.request.query_params.get("genres")
        actors = self.request.query_params.get("actors")

        queryset = self.queryset

        if title:
            queryset = queryset.filter(title__icontains=title)

        if genres:
            genres_ids = self._params_to_ints(genres)
            queryset = queryset.filter(genres__id__in=genres_ids)

        if actors:
            actors_ids = self._params_to_ints(actors)
            queryset = queryset.filter(actors__id__in=actors_ids)

        return queryset.distinct()

    def get_serializer_class(self):
        if self.action == "list":
            return MovieListSerializer

        if self.action == "retrieve":
            return MovieDetailSerializer

        if self.action == "upload_image":
            return MovieImageSerializer

        return MovieSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='title',
                location=OpenApiParameter.QUERY,
                required=False,
                description='Filter by partial movie title (case-insensitive).',
                type=str,
            ),
            OpenApiParameter(
                name='genres',
                location=OpenApiParameter.QUERY,
                required=False,
                description='Filter by genre IDs, comma-separated (e.g., 1,2).',
                type=str,
            ),
            OpenApiParameter(
                name='actors',
                location=OpenApiParameter.QUERY,
                required=False,
                description='Filter by actor IDs, comma-separated (e.g., 3,4).',
                type=str,
            ),
        ],
        operation_id='movie_list'
    )
    def list(self, request, *args, **kwargs):
        """List all movies with optional filtering."""
        # A implementação do list é a que herda do mixin e usa get_queryset
        return super().list(request, *args, **kwargs)
