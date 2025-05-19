from datetime import datetime

from django.db.models import F, Count
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import viewsets, mixins, status
from rest_framework.authentication import TokenAuthentication
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
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    @extend_schema(
        summary="Create Genre",
        description="It needs to create: name",
        methods=["POST"],
        tags=["genre"]
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Get all Genres",
        description="It shows the list with all Genres in format: "
                    "{ id, name }",
        methods=["GET"],
        tags=["genre"]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class ActorViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    queryset = Actor.objects.all()
    serializer_class = ActorSerializer
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    @extend_schema(
        summary="Get all Actors",
        description="Get all Actors in format: "
                    "id, first_name, last_name, full_name",
        methods=["GET"],
        tags=["actor"]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Create Actor",
        description="It needs for create: first_name, last_name, full_name",
        tags=["actor"],
        methods=["POST"]
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
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    @extend_schema(
        summary="Get all Cinema Halls ",
        description="Get all cinema halls in format: "
                    "{ id, name, rows, seats_in_row, capacity }",
        methods=["GET"],
        tags=["cinema_hall"],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Create Cinema Hall",
        description="It needs to create: "
                    "{ name, rows, seats_in_row, capacity }",
        methods=["POST"],
        tags=["cinema_hall"]
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
    authentication_classes = (TokenAuthentication,)
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
        summary="Upload Image",
        description="It takes images in all formats",
        tags=["movie"],
        methods=["POST"]
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
        summary="Get all Movies",
        description="Get all movies in format: "
                    "{ id, title, description, duration, genres, actors }",
        tags=["movie"],
        methods=["GET"],
        parameters=[
            OpenApiParameter(
                name="title",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Filtering by title",
            ),
            OpenApiParameter(
                name="genres",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Filtering by genres"
            ),
            OpenApiParameter(
                name="actors",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Filtering by actors"
            )
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Retrieve Movie",
        description="It can retrieve the movie by id",
        tags=["movie"],
        methods=["GET"],
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Create Movie",
        description="It needs to create "
                    "{ title, description, duration, genres, actors }",
        tags=["movie"],
        methods=["POST"],
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
    authentication_classes = (TokenAuthentication,)
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
        summary="Get all Movie Sessions",
        description="Get all movie Sessions in format: { "
                    "id, "
                    "show_time, "
                    "movie_title, "
                    "movie_image, "
                    "cinema_hall_name, "
                    "cinema_hall_capacity, "
                    "tickets_available "
                    "}",
        tags=["movie_session"],
        methods=["GET"],
        parameters=[
            OpenApiParameter(
                name="date",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filtering by show time",
                required=False,
                default="2024-10-15"
            ),
            OpenApiParameter(
                name="movie",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Filtering by { movie.id }",
                required=False,
                default=2
            )
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Create Movie Session",
        description="It needs to create: { "
                    "id, "
                    "show_time, "
                    "movie_title, "
                    "movie_image, "
                    "cinema_hall_name, "
                    "cinema_hall_capacity, "
                    "tickets_available "
                    "}",
        tags=["movie_session"],
        methods=["POST"]
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Retrieve Movie Session",
        description="Retrieve Movie Session by id",
        tags=["movie_session"],
        methods=["GET"]
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Update Movie Session",
        description=" It can update the Movie Session be fields: { "
                    "id, "
                    "show_time, "
                    "movie_title, "
                    "movie_image, "
                    "cinema_hall_name, "
                    "cinema_hall_capacity, "
                    "tickets_available "
                    "}",
        methods=["PUT"],
        tags=["movie_session"]
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Partial Update Movie Session",
        description="It can update Movie Session by not all fields",
        methods=["PATCH"],
        tags=["movie_session"]
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Destroy Movie Session",
        description="It can delete movie session by { id }",
        tags=["movie_session"],
        methods=["DELETE"]
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
    authentication_classes = (TokenAuthentication,)
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
        summary="Get Orders list",
        description="It get orders in format: { id, tickets, created_at }",
        methods=["GET"],
        tags=["order"]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Create Order",
        description="It needs to create: { tickets }",
        tags=["order"],
        methods=["POST"]
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
