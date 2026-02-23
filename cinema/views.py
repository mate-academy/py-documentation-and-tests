from datetime import datetime
from django.db.models import F, Count
from rest_framework import viewsets, mixins, status
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
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
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from rest_framework_simplejwt.authentication import JWTAuthentication

from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class GenreViewSet(mixins.CreateModelMixin,
                   mixins.ListModelMixin,
                   GenericViewSet):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)


class ActorViewSet(mixins.CreateModelMixin,
                   mixins.ListModelMixin,
                   GenericViewSet):
    queryset = Actor.objects.all()
    serializer_class = ActorSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)


class CinemaHallViewSet(mixins.CreateModelMixin,
                        mixins.ListModelMixin,
                        GenericViewSet):
    queryset = CinemaHall.objects.all()
    serializer_class = CinemaHallSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)


@extend_schema(
    parameters=[
        OpenApiParameter(
            name="title",
            type=OpenApiTypes.STR,
            description="Filtrar filmes por título "
                        "(correspondência parcial)",
        ),
        OpenApiParameter(
            name="genres",
            type=OpenApiTypes.INT,
            description="Filtrar filmes por ID de gênero "
                        "(separados por vírgula)",
        ),
        OpenApiParameter(
            name="actors",
            type=OpenApiTypes.INT,
            description="Filtrar filmes por ID de ator "
                        "(separados por vírgula)",
        ),
    ]
)
class MovieViewSet(viewsets.ModelViewSet):
    queryset = Movie.objects.prefetch_related("genres", "actors")
    serializer_class = MovieSerializer
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="title",
                description="Filter movies by title (partial match)",
                required=False,
                type=OpenApiTypes.STR,
            ),
            OpenApiParameter(
                name="genres",
                description="Filter movies by genre IDs (comma-separated)",
                required=False,
                type=OpenApiTypes.STR,
            ),
            OpenApiParameter(
                name="actors",
                description="Filter movies by actor IDs (comma-separated)",
                required=False,
                type=OpenApiTypes.STR,
            ),
        ]
    )
    def get_queryset(self):
        """Retrieve movies with optional filters."""
        queryset = self.queryset
        title = self.request.query_params.get("title")
        genres = self.request.query_params.get("genres")
        actors = self.request.query_params.get("actors")

        if title:
            queryset = queryset.filter(title__icontains=title)

        if genres:
            genre_ids = [int(x) for x in genres.split(",")]
            queryset = queryset.filter(genres__id__in=genre_ids)

        if actors:
            actor_ids = [int(x) for x in actors.split(",")]
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

    @action(
        detail=True,
        methods=["POST"],
        url_path="upload-image",
        permission_classes=[IsAdminUser],
    )
    def upload_image(self, request, pk=None):
        """Upload an image for a movie."""
        movie = self.get_object()
        serializer = self.get_serializer(movie, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
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
    ]
)
class MovieSessionViewSet(viewsets.ModelViewSet):
    queryset = (
        MovieSession.objects.all()
        .select_related("movie", "cinema_hall")
        .annotate(
            tickets_available=(F("cinema_hall__rows") * F("cinema_hall__seats_in_row") - Count("tickets"))
        )
    )
    serializer_class = MovieSessionSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    def get_queryset(self):
        queryset = self.queryset
        date_str = self.request.query_params.get("date")
        movie_id_str = self.request.query_params.get("movie")

        if date_str:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            queryset = queryset.filter(show_time__date=date_obj)

        if movie_id_str:
            queryset = queryset.filter(movie_id=int(movie_id_str))

        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return MovieSessionListSerializer
        if self.action == "retrieve":
            return MovieSessionDetailSerializer
        return MovieSessionSerializer


class OrderViewSet(mixins.CreateModelMixin,
                   mixins.ListModelMixin,
                   viewsets.GenericViewSet):
    queryset = Order.objects.prefetch_related(
        "tickets__movie_session__movie",
        "tickets__movie_session__cinema_hall"
    )
    serializer_class = OrderSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == "list":
            return OrderListSerializer
        return OrderSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
