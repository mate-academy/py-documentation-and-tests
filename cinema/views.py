from datetime import datetime

from django.db.models import F, Count
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (extend_schema,
                                   OpenApiParameter,
                                   extend_schema_view)
from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from cinema.models import Genre, Actor, CinemaHall, Movie, MovieSession, Order

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
        description="Returns list of all genres",
    ),
    create=extend_schema(
        summary="Create a genre",
        description="Create a new genre. Available only for admin/staff",
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
        description="Returns list of all actors",
    ),
    create=extend_schema(
        summary="Create an actor",
        description="Create a new actor. Available only for admin/staff",
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
        description="Returns list of all cinema halls",
    ),
    create=extend_schema(
        summary="Create a cinema hall",
        description="Create a new cinema hall. Available only for admin/staff",
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
        description="Returns list of all movies with optional"
                    " filtering by title, genres and actors",
        parameters=[
            OpenApiParameter(
                "title",
                type=OpenApiTypes.STR,
                description="Filter by movie title (case-insensitive)",
            ),
            OpenApiParameter(
                "genres",
                type={"type": "array", "items": {"type": "integer"}},
                style="form",
                explode=False,
                description="Filter by genre IDs."
                            " Format: Provide comma-separated IDs (1, 2, 3..)",
            ),
            OpenApiParameter(
                "actors",
                type={"type": "array", "items": {"type": "integer"}},
                style="form",
                explode=False,
                description="Filter by actor IDs."
                            " Format: Provide comma-separated IDs (1, 2, 3..)",
            ),
        ],
    ),
    create=extend_schema(
        summary="Create a movie",
        description="Create a new movie. Available only for admin/staff",
    ),
    retrieve=extend_schema(
        summary="Retrieve movie details",
        description="Get full details of a specific movie by ID",
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
        summary="Upload movie image",
        description="Upload a conver image for a specific movie."
                    " Only available for admin users and only on POST action",
        responses={200: MovieImageSerializer},
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
        description="Returns list of all movie sessions"
                    " with optional filtering by date and movie ID",
        parameters=[
            OpenApiParameter(
                "date",
                type=OpenApiTypes.DATE,
                description="Filter by movie session date",
            ),
            OpenApiParameter(
                "movie",
                type=OpenApiTypes.INT,
                style="form",
                explode=False,
                description="Filter by a single movie ID.",
            ),
        ],
    ),
    create=extend_schema(
        summary="Create a movie session",
        description="Create a new movie session."
                    " Available only for admin/staff",
    ),
    retrieve=extend_schema(
        summary="Retrieve movie details",
        description="Get full details of a specific movie session by ID",
    ),
    update=extend_schema(
        summary="Fully update a movie session",
        description="Fully update a movie session",
    ),
    partial_update=extend_schema(
        summary="Partially update a movie session",
        description="Partially update a movie session",
    ),
    destroy=extend_schema(
        summary="Delete a movie session",
        description="Delete a movie session. Only available for staff/admin",
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
        summary="List user orders",
        description="Retrieve a paginated"
                    " list of orders placed"
                    " by the current authenticated user",
    ),
    create=extend_schema(
        summary="Create an order",
        description="Create a new order for the current user."
                    " Provide a list of tickets to purchase",
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
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == "list":
            return OrderListSerializer

        return OrderSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
