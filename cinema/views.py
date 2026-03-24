from datetime import datetime

from django.db.models import F, Count
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    extend_schema,
    OpenApiExample,
    OpenApiParameter
)
from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.viewsets import GenericViewSet

from cinema.models import (
    Genre,
    Actor,
    CinemaHall,
    Movie,
    MovieSession,
    Order
)
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
        summary="List all genres",
        description="Returns a list of all available genres",
        responses={200: GenreSerializer},
    )
    def list(self, request: Request) -> Response:
        return super().list(request)

    @extend_schema(
        summary="Create a genre",
        description="Creates a new genre",
        request=GenreSerializer,
        responses={201: GenreSerializer},
        examples=[
            OpenApiExample(
                "Example request",
                value={
                    "name": "example_genre",
                },
                request_only=True,
            )
        ]
    )
    def create(self, request: Request, *args, **kwargs) -> Response:
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
        summary="List all actors",
        description="Returns a list of all available actors",
        responses={200: ActorSerializer},
    )
    def list(self, request: Request) -> Response:
        return super().list(request)

    @extend_schema(
        summary="Create an actor",
        description="Creates a new actor or actress",
        request=ActorSerializer,
        responses={201: ActorSerializer},
        examples=[
            OpenApiExample(
                "Example request",
                value={
                    "first_name": "First",
                    "last_name": "Last",
                },
                request_only=True,
            )
        ]
    )
    def create(self, request: Request, *args, **kwargs) -> Response:
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
        summary="List all cinema halls",
        description="Returns a list of all available cinema halls",
        responses={200: CinemaHallSerializer},
    )
    def list(self, request: Request) -> Response:
        return super().list(request)

    @extend_schema(
        summary="Create a cinema hall",
        description="Creates a new cinema hall",
        request=CinemaHallSerializer,
        responses={201: CinemaHallSerializer},
        examples=[
            OpenApiExample(
                "Example request",
                value={
                    "name": "new_cinema_hall",
                    "rows": 40,
                    "seats_in_row": 10
                },
                request_only=True,
            )
        ]
    )
    def create(self, request: Request, *args, **kwargs) -> Response:
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
        summary="Upload movie image",
        description="Upload an image to be added as movie image",
        request=MovieImageSerializer,
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

    @extend_schema(
        summary="List all movies",
        description="Returns a list of all available movies.",
        responses={200: MovieListSerializer},
        parameters=[
            OpenApiParameter(
                name="title",
                type=OpenApiTypes.STR,
                description="Filter by movie title (case-insensitive)",
            ),
            OpenApiParameter(
                name="genres",
                type=OpenApiTypes.STR,
                description=(
                    "Filter by genre IDs (comma-separated, e.g. '1,2,3')"
                ),
            ),
            OpenApiParameter(
                name="actors",
                type=OpenApiTypes.STR,
                description=(
                    "Filter by actor IDs (comma-separated, e.g. '1,2,3')"
                ),
            ),
        ],
    )
    def list(self, request: Request, *args, **kwargs) -> Response:
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Get a movie",
        description="Returns a movie by its pk.",
        responses={200: MovieDetailSerializer},
        examples=[
            OpenApiExample(
                "Example response",
                value={
                    "id": 1,
                    "title": "Title",
                    "description": "description",
                    "duration": 150,
                    "genres": [
                        {
                            "id": 1,
                            "name": "genre"
                        }
                    ],
                    "actors": [
                        {
                            "id": 1,
                            "first_name": "First",
                            "last_name": "Last",
                            "full_name": "string"
                        }
                    ],
                    "image": "string"
                },
                response_only=True,
            )
        ],
    )
    def retrieve(self, request: Request, *args, **kwargs) -> Response:
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Create a movie",
        description="Create a movie",
        request=MovieSerializer,
        responses={201: MovieSerializer},
        examples=[
            OpenApiExample(
                "Example request",
                value={
                    "title": "movie",
                    "description": "new cool movie",
                    "duration": 300,
                    "genres": [
                        1, 2
                    ],
                    "actors": [
                        1, 2
                    ]
                },
                request_only=True,
            )
        ]
    )
    def create(self, request: Request, *args, **kwargs) -> Response:
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
        summary="List all movie sessions",
        description="Returns a list of all available movie sessions.",
        responses={200: MovieSessionListSerializer},
        parameters=[
            OpenApiParameter(
                name="date",
                type=OpenApiTypes.DATE,
                description="Filter by date (e.g. '2022-09-02')",
            ),
            OpenApiParameter(
                name="movie",
                type=OpenApiTypes.INT,
                description="Filter by movie ID",
            ),
        ],
    )
    def list(self, request: Request, *args, **kwargs) -> Response:
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Get a movie session",
        description="Returns a movie session by its pk",
        responses={200: MovieSessionDetailSerializer},
        examples=[
            OpenApiExample(
                "Example response",
                value={
                    "id": 0,
                    "show_time": "2026-03-24T20:46:44.603Z",
                    "movie": {
                        "id": 0,
                        "title": "string",
                        "description": "string",
                        "duration": 9223372036854776000,
                        "genres": [
                            "string"
                        ],
                        "actors": [
                            "string"
                        ],
                        "image": "string"
                    },
                    "cinema_hall": {
                        "id": 0,
                        "name": "string",
                        "rows": 9223372036854776000,
                        "seats_in_row": 9223372036854776000,
                        "capacity": 0
                    },
                    "taken_places": [
                        {
                            "row": 9223372036854776000,
                            "seat": 9223372036854776000
                        }
                    ]
                },
                response_only=True,
            )
        ],
    )
    def retrieve(self, request: Request, *args, **kwargs) -> Response:
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Create a movie session",
        description=(
            "Creates a movie session"
        ),
        request=MovieSessionSerializer,
        responses={201: MovieSessionSerializer},
        examples=[
            OpenApiExample(
                "Example request",
                value={
                    "show_time": "2026-03-24T20:53:15.709Z",
                    "movie": 0,
                    "cinema_hall": 0
                },
                request_only=True,
            )
        ]
    )
    def create(self, request: Request, *args, **kwargs) -> Response:
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Update a movie session",
        description="Updates all fields of a movie session by its pk",
        request=MovieSessionSerializer,
        responses={200: MovieSessionSerializer},
        examples=[
            OpenApiExample(
                "Example request",
                value={
                    "show_time": "2026-03-24T20:53:15.709Z",
                    "movie": 0,
                    "cinema_hall": 0
                },
                request_only=True,
            )
        ]
    )
    def update(self, request: Request, *args, **kwargs) -> Response:
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Partially update a movie session",
        description="Updates one or more fields of a movie session by its pk",
        request=MovieSessionSerializer,
        responses={200: MovieSessionSerializer},
        examples=[
            OpenApiExample(
                "Example request",
                value={
                    "show_time": "2026-03-24T20:53:15.709Z",
                },
                request_only=True,
            )
        ]
    )
    def partial_update(self, request: Request, *args, **kwargs) -> Response:
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Delete a movie session",
        description="Deletes a movie session by its pk",
        responses={204: None},
    )
    def destroy(self, request: Request, *args, **kwargs) -> Response:
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
        summary="List user orders",
        description=(
            "Returns a list of orders for the currently authenticated user"
        ),
        responses={200: OrderListSerializer},
    )
    def list(self, request: Request) -> Response:
        return super().list(request)

    @extend_schema(
        summary="Create an order",
        description=(
            "Creates a order for the currently authenticated user"
        ),
        responses={201: OrderSerializer},
        examples=[
            OpenApiExample(
                "Example request",
                value={
                    "tickets": [
                        {
                            "row": 2,
                            "seat": 9,
                            "movie_session": 1
                        },
                        {
                            "row": 3,
                            "seat": 2,
                            "movie_session": 1
                        }
                    ]
                },
                request_only=True,
            )
        ]
    )
    def create(self, request: Request, *args, **kwargs) -> Response:
        return super().create(request, *args, **kwargs)
