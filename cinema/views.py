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
        summary="Get list of genres",
        description="Retrieve a list of all genres.",
    )
    def list(self, request, *args, **kwargs):
        """Get list of genres"""
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Create genre",
        description="Create a new genre.",
    )
    def create(self, request, *args, **kwargs):
        """Create genre"""
        return super().create(request, *args, **kwargs)


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
        summary="Get list of actors",
        description="Retrieve a list of all actors.",
    )
    def list(self, request, *args, **kwargs):
        """Get list of actors"""
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Create actor",
        description="Create a new actor.",
    )
    def create(self, request, *args, **kwargs):
        """Create actor"""
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
        summary="Get list of cinema halls",
        description="Retrieve a list of all cinema halls.",
    )
    def list(self, request, *args, **kwargs):
        """Get list of cinema halls"""
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Create cinema hall",
        description="Create a new cinema hall.",
    )
    def create(self, request, *args, **kwargs):
        """Create cinema hall"""
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
        summary="Create movie",
        description="Create a new movie.",
    )
    def create(self, request, *args, **kwargs):
        """Create movie"""
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Get movie details",
        description="Retrieve detailed information about a specific movie.",
    )
    def retrieve(self, request, *args, **kwargs):
        """Get movie details"""
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Upload movie image",
        description="Upload an image for a specific movie.",
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

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "title",
                type=str,
                description="Filter movies by title. Example: ?title=Movie",
                required=False,
            ),
            OpenApiParameter(
                "genres",
                type=int,
                description="Comma-separated list of genre IDs. Example: ?grenres=1,2,3",
                required=False,
            ),
            OpenApiParameter(
                "actors",
                type=int,
                description="Comma-separated list of actor IDs. Example: ?actors=1,2,3",
                required=False,
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        """Get list of movies"""
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
        summary="Get list of movie sessions",
        description="Retrieve movie sessions with optional filters.",
        parameters=[
            OpenApiParameter(
                "date",
                type=str,
                description="Filter sessions by date. Format: YYYY-MM-DD.",
                required=False,
            ),
            OpenApiParameter(
                "movie",
                type=int,
                description="Filter sessions by movie ID.",
                required=False,
            ),
        ],
    )
    def list(self, request, *args, **kwargs):
        """Get list of movie sessions"""
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Create movie session",
        description="Create a new movie session.",
    )
    def create(self, request, *args, **kwargs):
        """Create movie session"""
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Get movie session details",
        description="Retrieve detailed information about a specific movie session.",
    )
    def retrieve(self, request, *args, **kwargs):
        """Get movie session details"""
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Update movie session",
        description="Completely update an existing movie session.",
    )
    def update(self, request, *args, **kwargs):
        """Update movie session"""
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Partially update movie session",
        description="Partially update an existing movie session.",
    )
    def partial_update(self, request, *args, **kwargs):
        """Partially update movie session"""
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Delete movie session",
        description="Delete an existing movie session.",
    )
    def destroy(self, request, *args, **kwargs):
        """Delete movie session"""
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
        "tickets__movie_session__movie",
        "tickets__movie_session__cinema_hall",
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
        summary="Get user's orders",
        description="Retrieve a paginated list of orders belonging to the authenticated user.",
    )
    def list(self, request, *args, **kwargs):
        """Get list of orders"""
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Create order",
        description="Create a new order for the authenticated user.",
    )
    def create(self, request, *args, **kwargs):
        """Create order"""
        return super().create(request, *args, **kwargs)