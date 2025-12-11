from datetime import datetime

from django.db.models import F, Count
from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter

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
    viewsets.GenericViewSet,
):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    def list(self, request, *args, **kwargs):
        """Get list of genres"""
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        """Create a new genre"""
        return super().create(request, *args, **kwargs)


class ActorViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Actor.objects.all()
    serializer_class = ActorSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    def list(self, request, *args, **kwargs):
        """Get list of actors"""
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        """Create a new actor"""
        return super().create(request, *args, **kwargs)


class CinemaHallViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = CinemaHall.objects.all()
    serializer_class = CinemaHallSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    def list(self, request, *args, **kwargs):
        """Get list of cinema halls"""
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        """Create a new cinema hall"""
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

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="title",
                type={"type": "string"},
                description="Filter by title substring",
            ),
            OpenApiParameter(
                name="genres",
                type={"type": "array", "items": {"type": "integer"}},
                description="Filter by genres IDs (comma separated)",
            ),
            OpenApiParameter(
                name="actors",
                type={"type": "array", "items": {"type": "integer"}},
                description="Filter by actors IDs (comma separated)",
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        """Get list of movies"""
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        """Create a new movie"""
        return super().create(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        """Retrieve a movie"""
        return super().retrieve(request, *args, **kwargs)


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
                type={"type": "string", "format": "date"},
                description="Filter by show date (YYYY-MM-DD)",
            ),
            OpenApiParameter(
                name="movie",
                type={"type": "integer"},
                description="Filter by movie ID",
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        """Get list of movie sessions"""
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        """Create a new movie session"""
        return super().create(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        """Retrieve a movie session"""
        return super().retrieve(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        """Update a movie session"""
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        """Partially update a movie session"""
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Delete a movie session"""
        return super().destroy(request, *args, **kwargs)


class OrderPagination(PageNumberPagination):
    page_size = 10
    max_page_size = 100


class OrderViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
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
        """Get list of orders for the authenticated user"""
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        """Create a new order for the authenticated user"""
        return super().create(request, *args, **kwargs)
