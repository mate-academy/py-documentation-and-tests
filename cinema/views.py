from datetime import datetime
from django.utils.dateparse import parse_date
from rest_framework.exceptions import ParseError
from django.db.models import F, Count
from rest_framework import viewsets, mixins, status
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ReadOnlyModelViewSet
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
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


class ActorViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    queryset = Actor.objects.all()
    serializer_class = ActorSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)


class CinemaHallViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    queryset = CinemaHall.objects.all()
    serializer_class = CinemaHallSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)


class MovieViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Movie.objects.prefetch_related("genres", "actors")
    serializer_class = MovieSerializer
    permission_classes = (IsAuthenticated,)

    def get_permissions(self):
        if self.action in ("create", "upload_image"):
            return [IsAdminUser()]
        return super().get_permissions()

    @staticmethod
    def _params_to_ints(qs):
        """Converts a list of string IDs to a list of integers"""
        return [int(str_id) for str_id in qs.split(",")]

    def create(self, request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied("Only admin can create movies.")
        return super().create(request, *args, **kwargs)

    def get_queryset(self):
        """Retrieve the movies with filters"""
        title = self.request.query_params.get("title")
        genres = self.request.query_params.get("genres")
        actors = self.request.query_params.get("actors")

        queryset = super().get_queryset() if (
            hasattr(super(), "get_queryset")) \
            else self.queryset

        if title:
            queryset = queryset.filter(title__icontains=title)

        if genres:
            genre_ids = self._parse_id_list(genres, "genres")
            if genre_ids:
                queryset = queryset.filter(genres__id__in=genre_ids)

        if actors:
            actor_ids = self._parse_id_list(actors, "actors")
            if actor_ids:
                queryset = queryset.filter(actors__id__in=actor_ids)

        return queryset.distinct()

    def get_serializer_class(self):
        if self.action == "list":
            return MovieListSerializer

        if self.action == "retrieve":
            return MovieDetailSerializer

        if self.action == "upload_image":
            return MovieImageSerializer

        return MovieSerializer

    @staticmethod
    def _parse_id_list(csv_value, field_name):
        ids = []
        for raw in csv_value.split(","):
            token = raw.strip()
            if not token:
                continue
            try:
                ids.append(int(token))
            except (TypeError, ValueError):
                raise ParseError(
                    f"Invalid '{field_name}' parameter. "
                    f"Use comma-separated integers, e.g. '{field_name}=1,2,3'."
                )
        return ids

    def get_throttles(self):
        if getattr(self, "action", None) == "upload_image":
            return []
        return super().get_throttles()

    @action(
        methods=["POST"],
        detail=True,
        url_path="upload-image",
        permission_classes=[IsAdminUser],
    )
    def upload_image(self, request, pk=None):
        """Endpoint for uploading image to specific movie"""
        if not request.user.is_staff:
            raise PermissionDenied("Only admin can upload images.")
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
                description="Case-insensitive "
                            "substring match on movie title. "
                            "Example: `?title=man`",
                required=False,
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="genres",
                description="Comma-separated genre IDs "
                            "(OR-filter). Example: `?genres=1,3`",
                required=False,
                type=OpenApiTypes.STR,  # "1,2,3"
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="actors",
                description="Comma-separated actor "
                            "IDs (OR-filter). Example: `?actors=4,5`",
                required=False,
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
            ),
        ],
        description="List movies with optional "
                    "filters by title, genres and actors.",
    )
    def list(self, request, *args, **kwargs):
        """Documented list for Swagger (filters: title, genres, actors)."""
        return super().list(request, *args, **kwargs)


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
        date_str = self.request.query_params.get("date")
        movie_str = self.request.query_params.get("movie")

        queryset = super().get_queryset() if (
            hasattr(super(), "get_queryset")) \
            else self.queryset

        if date_str:
            dt = parse_date(date_str)
            if dt is None:
                raise ParseError(
                    "Invalid 'date' parameter. "
                    "Expected format YYYY-MM-DD, e.g. '2025-03-01'."
                )
            queryset = queryset.filter(show_time__date=dt)

        if movie_str:
            try:
                movie_id = int(movie_str)
            except (TypeError, ValueError):
                raise ParseError(
                    "Invalid 'movie' parameter. "
                    "Expected integer id, e.g. 'movie=7'."
                )
            queryset = queryset.filter(movie_id=movie_id)

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
                description="Filter by show date (YYYY-MM-DD). "
                            "Example: `?date=2025-09-01`",
                required=False,
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="movie",
                description="Filter by movie ID. Example: `?movie=1`",
                required=False,
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
            ),
        ],
        description="List movie sessions filtered by date and/or movie.",
    )
    def list(self, request, *args, **kwargs):
        """Documented list for Swagger (filters: date, movie)."""
        return super().list(request, *args, **kwargs)


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
