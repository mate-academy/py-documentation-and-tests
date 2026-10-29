from datetime import datetime

from django.db.models import F, Count
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiParameter,
)
from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework.exceptions import ValidationError

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


@extend_schema_view(
    list=extend_schema(
        summary="List genres",
        description="Returns all movie genres. "
                    "Available to any authenticated user.",
    ),
    create=extend_schema(
        summary="Create a genre",
        description="Creates a new genre. Allowed for admin users only.",
    ),
)
class GenreViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer


@extend_schema_view(
    list=extend_schema(
        summary="List actors",
        description="Returns all actors. "
                    "Available to any authenticated user.",
    ),
    create=extend_schema(
        summary="Create an actor",
        description="Creates a new actor. Fields first_name and last_name "
                    "are required. Allowed for admin users only.",
    ),
)
class ActorViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    queryset = Actor.objects.all()
    serializer_class = ActorSerializer


@extend_schema_view(
    list=extend_schema(
        summary="List cinema halls",
        description="Returns all cinema halls with their rows, "
                    "seats in a row and total capacity.",
    ),
    create=extend_schema(
        summary="Create a cinema hall",
        description="Creates a new cinema hall. "
                    "Allowed for admin users only.",
    ),
)
class CinemaHallViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    queryset = CinemaHall.objects.all()
    serializer_class = CinemaHallSerializer


@extend_schema_view(
    list=extend_schema(
        summary="List movies",
        description="Returns movies with optional filtering "
                    "by title, genres and actors.",
        parameters=[
            OpenApiParameter(
                name="title",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description=(
                    "Filter by movie title, case-insensitive partial "
                    "match (ex. ?title=inter)"
                ),
            ),
            OpenApiParameter(
                name="genres",
                type={"type": "array", "items": {"type": "number"}},
                location=OpenApiParameter.QUERY,
                description=(
                    "Filter by genre ids, comma-separated list "
                    "(ex. ?genres=2,5)"
                ),
            ),
            OpenApiParameter(
                name="actors",
                type={"type": "array", "items": {"type": "number"}},
                location=OpenApiParameter.QUERY,
                description=(
                    "Filter by actor ids, comma-separated list "
                    "(ex. ?actors=1,3)"
                ),
            ),
        ],
    ),
    retrieve=extend_schema(
        summary="Retrieve a movie",
        description="Returns detailed movie information "
                    "with its genres and actors.",
    ),
    create=extend_schema(
        summary="Create a movie",
        description="Creates a new movie. Allowed for admin users only.",
    ),
)
class MovieViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Movie.objects.prefetch_related("genres", "actors")
    serializer_class = MovieSerializer

    @staticmethod
    def _params_to_ints(qs):
        """Converts a list of string IDs to a list of integers"""
        try:
            return [int(str_id) for str_id in qs.split(",")]
        except ValueError:
            raise ValidationError(
                "Must be a comma-separated list of integers (ex. 1,3)"
            )

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
        summary="Upload a movie image",
        description="Uploads an image for the specific movie. "
                    "Allowed for admin users only.",
    )
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


@extend_schema_view(
    list=extend_schema(
        summary="List movie sessions",
        description="Returns movie sessions with the number of available "
                    "tickets and optional filtering by date and movie.",
        parameters=[
            OpenApiParameter(
                name="date",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description=(
                    "Filter by the date of the show time in the "
                    "YYYY-MM-DD format (ex. ?date=2022-10-23)"
                ),
            ),
            OpenApiParameter(
                name="movie",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter by movie id (ex. ?movie=4)",
            ),
        ],
    ),
    retrieve=extend_schema(
        summary="Retrieve a movie session",
        description="Returns detailed movie session information with the "
                    "cinema hall and the list of taken places.",
    ),
    create=extend_schema(
        summary="Create a movie session",
        description="Creates a new movie session. "
                    "Allowed for admin users only.",
    ),
    update=extend_schema(
        summary="Update a movie session",
        description="Fully updates the movie session. "
                    "Allowed for admin users only.",
    ),
    partial_update=extend_schema(
        summary="Partially update a movie session",
        description="Updates the given fields of the movie session. "
                    "Allowed for admin users only.",
    ),
    destroy=extend_schema(
        summary="Delete a movie session",
        description="Deletes the movie session. "
                    "Allowed for admin users only.",
    ),
)
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


class OrderPagination(PageNumberPagination):
    page_size = 10
    max_page_size = 100


@extend_schema_view(
    list=extend_schema(
        summary="List own orders",
        description="Returns the paginated list of orders of the current "
                    "authenticated user with their tickets.",
        parameters=[
            OpenApiParameter(
                name="page",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Number of the page of results to return "
                            "(10 orders per page)",
            ),
        ],
    ),
    create=extend_schema(
        summary="Create an order",
        description="Creates an order with tickets for the current "
                    "authenticated user. Each ticket requires "
                    "movie_session, row and seat.",
    ),
)
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

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == "list":
            return OrderListSerializer

        return OrderSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
