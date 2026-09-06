from datetime import datetime

from django.db.models import F, Count
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from cinema.models import Genre, Actor, CinemaHall, Movie, MovieSession, Order
from cinema.permissions import IsAdminOrIfAuthenticatedReadOnly

from cinema.serializers import (
    GenreSerializer,
    ActorSerializer,
    CinemaHallSerializer,
    MovieSerializer,
    MovieSessionSerializer,
    MovieSessionListSerializer,
    MovieDetailSerializer,
    MovieSessionDetailSerializer,
    MovieListSerializer,
    OrderSerializer,
    OrderListSerializer,
    MovieImageSerializer,
)


class GenreViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    def list(self, request, *args, **kwargs):
        """Get a list of genres."""
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        """Create a genre."""
        return super().create(request, *args, **kwargs)


class ActorViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    queryset = Actor.objects.all()
    serializer_class = ActorSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    def list(self, request, *args, **kwargs):
        """Get a list of actors."""
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        """Create an actor."""
        return super().create(request, *args, **kwargs)


class CinemaHallViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    queryset = CinemaHall.objects.all()
    serializer_class = CinemaHallSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    def list(self, request, *args, **kwargs):
        """Get a list of cinema halls."""
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        """Create a cinema hall."""
        return super().create(request, *args, **kwargs)


class MovieViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Movie.objects.prefetch_related("genres", "actors")
    serializer_class = MovieSerializer
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
                name="title",
                type={"type": "string"},
                description="Filter by movie title (ex. ?title=Un)",
            ),
            OpenApiParameter(
                name="genres",
                type={"type": "array", "items": {"type": "integer"}},
                style="form",
                explode=False,
                description="Filter by genre id (ex. ?genres=1,2)",
            ),
            OpenApiParameter(
                name="actors",
                type={"type": "array", "items": {"type": "integer"}},
                style="form",
                explode=False,
                description="Filter by actor id (ex. ?actors=1,2)",
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        """Get a list of movies."""
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        """Create a movie."""
        return super().create(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        """Get a movie by id."""
        return super().retrieve(request, *args, **kwargs)

    @action(
        methods=["POST"],
        detail=True,
        url_path="upload-image",
        permission_classes=[IsAdminUser],
    )
    def upload_image(self, request, pk=None):
        """Endpoint for uploading image to specific movie"""
        movie = self.get_object()
        serializer = self.get_serializer(movie, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MovieSessionViewSet(viewsets.ModelViewSet):
    queryset = (
        MovieSession.objects.all()
        .select_related("movie", "cinema_hall")
        .annotate(
            tickets_available=(
                F("cinema_hall__rows") * F("cinema_hall__seats_in_row")
                - Count("tickets")
            )
        )
    )
    serializer_class = MovieSessionSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    def get_queryset(self):
        date = self.request.query_params.get("date")
        movie_id_str = self.request.query_params.get("movie")

        queryset = self.queryset

        if date:
            date = datetime.strptime(date, "%Y-%m-%d").date()
            queryset = queryset.filter(show_time__date=date)

        if movie_id_str:
            queryset = queryset.filter(movie_id=int(movie_id_str))

        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return MovieSessionListSerializer

        if self.action == "retrieve":
            return MovieSessionDetailSerializer

        return MovieSessionSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="date",
                type={"type": "string"},
                description=(
                    "Filter by movie session date (ex. ?date=2026-05-13)"
                ),
            ),
            OpenApiParameter(
                name="movie",
                type={"type": "integer"},
                description="Filter by movie id (ex. ?movie=1)",
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        """Get a list of movie sessions."""
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        """Get a movie session by id."""
        return super().retrieve(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        """Create a movie session."""
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        """Update movie session by id."""
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        """Partial update movie session by id."""
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Delete movie session by id."""
        return super().destroy(request, *args, **kwargs)


class OrderPagination(PageNumberPagination):
    page_size = 10
    max_page_size = 100


class OrderViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    GenericViewSet,
):
    queryset = Order.objects.prefetch_related(
        "tickets__movie_session__movie", "tickets__movie_session__cinema_hall"
    )
    serializer_class = OrderSerializer
    pagination_class = OrderPagination
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == "list":
            return OrderListSerializer

        return OrderSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def list(self, request, *args, **kwargs):
        """Get a list of orders for the logged in user."""
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        """Create an order."""
        return super().create(request, *args, **kwargs)
