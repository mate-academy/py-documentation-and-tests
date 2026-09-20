from datetime import datetime

from django.db.models import F, Count
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

from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiParameter,
)
from drf_spectacular.types import OpenApiTypes


@extend_schema_view(
    create=extend_schema(
        parameters=[
            OpenApiParameter(
                name="genres",
                description="Create a new gerne",
                required=True,
                type=OpenApiTypes.STR,
            ),
        ],
    ),
    list=extend_schema(
        description="List all genres",
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
    create=extend_schema(
        parameters=[
            OpenApiParameter(
                name="first_name",
                description="First name of the actor",
                required=True,
                type=OpenApiTypes.STR,
            ),
            OpenApiParameter(
                name="last_name",
                description="Last name of the actor",
                required=True,
                type=OpenApiTypes.STR,
            ),
        ],
        description="Create a new actor",
    ),
    list=extend_schema(description="List all actors"),
)
class ActorViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    queryset = Actor.objects.all()
    serializer_class = ActorSerializer


@extend_schema_view(
    create=extend_schema(
        parameters=[
            OpenApiParameter(
                name="name",
                required=True,
                description="Name of the cinema hall"
            ),
            OpenApiParameter(
                name="rows",
                required=True,
                description="Number of rows in the cinema hall"
            ),
            OpenApiParameter(
                name="seats_in_row",
                required=True,
                description="Number of seats in each row"
            ),
        ],
        description="Create a new cinema hall",
    ),
    list=extend_schema(description="List all cinema halls"),
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
        description="""List all movies with
        optional filters for title, genres, and actors""",
        parameters=[
            OpenApiParameter(
                name="title",
                description="Filter movies by title",
                required=False,
                type=OpenApiTypes.STR,
            ),
            OpenApiParameter(
                name="genres",
                description="Filter movies by genres (comma-separated IDs)",
                required=False,
                type=OpenApiTypes.STR,
            ),
            OpenApiParameter(
                name="actors",
                description="Filter movies by actors (comma-separated IDs)",
                required=False,
                type=OpenApiTypes.STR,
            ),
        ],
    ),
    create=extend_schema(
        description="Create a new movie",
        parameters=[
            OpenApiParameter(
                name="title",
                description="Title of the movie",
                required=True,
                type=OpenApiTypes.STR,
            ),
            OpenApiParameter(
                name="description",
                description="Description of the movie",
                required=True,
                type=OpenApiTypes.STR,
            ),
            OpenApiParameter(
                name="duration",
                description="Duration of the movie in minutes",
                required=True,
                type=OpenApiTypes.INT,
            ),
            OpenApiParameter(
                name="genres",
                description="""List of genre IDs associated
                with the movie (comma-separated)""",
                required=True,
                type=OpenApiTypes.STR,
            ),
            OpenApiParameter(
                name="actors",
                description="""List of actor IDs associated
                with the movie (comma-separated)""",
                required=True,
                type=OpenApiTypes.STR,
            ),
        ],
    ),
    retrieve=extend_schema(
        description="Retrieve details of a movie by ID",
    ),
    upload_image=extend_schema(),
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
        description="List all movie sessions, filtered by date and movie",
        parameters=[
            OpenApiParameter(
                name="date",
                description="Filter movie sessions by date (YYYY-MM-DD)",
                required=False,
                type=OpenApiTypes.DATE,
            ),
            OpenApiParameter(
                name="movie",
                description="Filter movie sessions by movie ID",
                required=False,
                type=OpenApiTypes.INT,
            ),
        ],
    ),
    create=extend_schema(
        description="Create a new movie session",
        parameters=[
            OpenApiParameter(
                name="show_time",
                description="""Show time of the movie
                session (YYYY-MM-DDTHH:MM:SSZ)""",
                required=True,
                type=OpenApiTypes.DATETIME,
            ),
            OpenApiParameter(
                name="movie",
                description="ID of the movie for the session",
                required=True,
                type=OpenApiTypes.INT,
            ),
            OpenApiParameter(
                name="cinema_hall",
                description="ID of the cinema hall for the session",
                required=True,
                type=OpenApiTypes.INT,
            ),
        ],
    ),
    retrieve=extend_schema(
        description="Retrieve details of a movie session by ID",
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
        description="List all orders for the authenticated user",
    ),
    create=extend_schema(
        description="Create a new order for the authenticated user",
        parameters=[
            OpenApiParameter(
                name="tickets",
                description="List of tickets for the order",
                required=True,
                type=OpenApiTypes.STR,
            )
        ],
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
        return Order.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == "list":
            return OrderListSerializer

        return OrderSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
