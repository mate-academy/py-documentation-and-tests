from datetime import datetime

from django.db.models import Count, F
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ReadOnlyModelViewSet

from cinema.models import Actor, CinemaHall, Genre, Movie, MovieSession, Order
from cinema.permissions import IsAdminOrIfAuthenticatedReadOnly
from cinema.serializers import (ActorSerializer, CinemaHallSerializer,
                                GenreSerializer, MovieDetailSerializer,
                                MovieImageSerializer, MovieListSerializer,
                                MovieSerializer, MovieSessionDetailSerializer,
                                MovieSessionListSerializer,
                                MovieSessionSerializer, OrderListSerializer,
                                OrderSerializer)


class GenreViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    # authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)


class ActorViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    queryset = Actor.objects.all()
    serializer_class = ActorSerializer
    # authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)


class CinemaHallViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    queryset = CinemaHall.objects.all()
    serializer_class = CinemaHallSerializer
    # authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)


class MovieViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Movie.objects.prefetch_related("genres", "actors")
    serializer_class = MovieSerializer
    # authentication_classes = (TokenAuthentication,)
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
                "title",
                required=False,
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter movie by title (icontains)",
            ),
            OpenApiParameter(
                "genres",
                required=False,
                type={"type": "array", "items": {"type": "number"}},
                description="Filter by genre id (Exemple: ?genres=1,2)",
            ),
            OpenApiParameter(
                "actors",
                required=False,
                type={"type": "array", "items": {"type": "number"}},
                location=OpenApiParameter.QUERY,
                description="Filter by actor id (Exemple: ?actors=1,2)",
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        """Endpoint for listing movies
         with optional filters (title, genres, actors)"""
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
        parameters=[
            OpenApiParameter(
                "date",
                required=False,
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description="Filter by show time date (Exemple: 2024-10-09)",
            ),
            OpenApiParameter(
                "movie",
                required=False,
                type={"type": "array", "items": {"type": "number"}},
                location=OpenApiParameter.QUERY,
                description="Filter by movie id (Exemple: ?movie=1,2)",
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        """Endpoint for listing movie session
         with optional filters (date, movie)"""
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
    # authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == "list":
            return OrderListSerializer

        return OrderSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
