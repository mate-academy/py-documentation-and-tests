from datetime import datetime

from django.db.models import F, Count
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiExample
)
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

    @extend_schema(
        description="Get list of all genres."
                    "No authentication required for viewing.",
        summary="Get list of all genres.",
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        description="Create a new genre. Admin permission required.",
        summary="Create a new genre.",
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)


class ActorViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    queryset = Actor.objects.all()
    serializer_class = ActorSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    @extend_schema(
        description="Get list of all actors. "
                    "No authentication required for viewing.",
        summary="List all actors"
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        description="Create a new actor. Admin permission required.",
        summary="Create actor"
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)


class CinemaHallViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    queryset = CinemaHall.objects.all()
    serializer_class = CinemaHallSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    @extend_schema(
        description="Get list of all cinema halls with their capacity. "
                    "No authentication required for viewing.",
        summary="List all cinema halls"
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        description="Create a new cinema hall. Admin permission required.",
        summary="Create cinema hall"
    )
    def create(self, request, *args, **kwargs):
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
        description="""Get list of movies with optional filtering.

            You can filter movies by:
            - **title**: Filter by movie title (case-insensitive partial match)
            - **genres**: Filter by genre IDs (comma-separated list)
            - **actors**: Filter by actor IDs (comma-separated list)

            **Note**: All filters can be used separately or combined.
            """,
        summary="List movies with filtering",
        parameters=[
            OpenApiParameter(
                name="title",
                description="Filter by movie title "
                            "(partial match, case-insensitive)",
                type=OpenApiTypes.STR,
                required=False,
                examples=[
                    OpenApiExample(
                        "Search for movie containing 'avatar'",
                        value="avatar",
                    ),
                ],
            ),
            OpenApiParameter(
                name="genres",
                description="Filter movie by genre IDs. "
                            "Provide a comma-separated list of genre IDs",
                type=OpenApiTypes.STR,
                required=False,
                examples=[
                    OpenApiExample(
                        "Movies in Crime (ID: 1) and Action (ID: 4) genres",
                        value="1,4",
                    ),
                    OpenApiExample(
                        "Movie only in Drama genre (ID: 2)",
                        value="2"
                    ),
                ],
            ),
            OpenApiParameter(
                name="actors",
                description="Filter movies by actor IDs. "
                            "Provide a comma-separated list of actor IDs",
                type=OpenApiTypes.STR,
                required=False,
                examples=[
                    OpenApiExample(
                        "Movies featuring actors with IDs 1 and 2",
                        value="1,2"
                    ),
                ],
            ),
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        description="Get detailed information about a specific movie "
                    "including all genres and actors.",
        summary="Get movie details"
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        description="Create a new movie. Admin permission required.",
        summary="Create movie"
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)


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
    # authentication_classes = (TokenAuthentication,)
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
        description="""Get a list of all movie sessions
            with optional filtering.

            You can filter movie sessions by:
            - **date**: Filter by specific date (format: YYYY-MM-DD)
            - **movie**: Filter by movie ID

            **Note**: Filters can be used separately or combined.
            Each session includes information about available tickets.
            """,
        summary="List movie sessions with filtering",
        parameters=[
            OpenApiParameter(
                name="date",
                description="Filter by specific date (format: YYYY-MM-DD)",
                type=OpenApiTypes.DATE,
                required=False,
                examples=[
                    OpenApiExample(
                        "Session on January 15, 2024",
                        value="2024-01-15"
                    ),
                ],
            ),
            OpenApiParameter(
                name="movie",
                description="Filter movie sessions by specific movie ID",
                type=OpenApiTypes.INT,
                required=False,
                examples=[
                    OpenApiExample("Session for movie with ID: 1", value=1),
                ],
            ),
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        description="Get detailed information about a specific movie session "
                    "including taken seats and cinema hall details.",
        summary="Get movie session details"
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        description="Create a new movie session. Admin permission required.",
        summary="Create movie session"
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        description="Update a movie session. Admin permission required.",
        summary="Update movie session"
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        description="Partially update a movie session. "
                    "Admin permission required.",
        summary="Partial update movie session"
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        description="Delete a movie session. Admin permission required.",
        summary="Delete movie session"
    )
    def destroy(self, request, *args, **kwargs):
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

    @extend_schema(
        description="Get list of user's orders. Authentication required.",
        summary="List user orders"
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        description="Create a new order with tickets."
                    " Authentication required.",
        summary="Create order"
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
