from django.db.models import F, Count
from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework_simplejwt.authentication import JWTAuthentication

from cinema.models import Genre, Actor, CinemaHall, Movie, MovieSession, Order
from cinema.permissions import IsAdminOrIfAuthenticatedReadOnly
from cinema.serializers import (
    GenreSerializer,
    ActorSerializer,
    CinemaHallSerializer,
    MovieSerializer,
    OrderSerializer,
    MovieImageSerializer,
    MovieSessionSerializer,
    MovieSessionListSerializer,
    MovieSessionDetailSerializer, MovieListSerializer, MovieDetailSerializer,
)


class GenreViewSet(
    mixins.CreateModelMixin, mixins.ListModelMixin, GenericViewSet
):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    @extend_schema(description="Retrieve a list of genres or create a new one")
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class ActorViewSet(
    mixins.CreateModelMixin, mixins.ListModelMixin, GenericViewSet
):
    queryset = Actor.objects.all()
    serializer_class = ActorSerializer
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    @extend_schema(description="Retrieve a list of actors or create a new one")
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class CinemaHallViewSet(
    mixins.CreateModelMixin, mixins.ListModelMixin, GenericViewSet
):
    queryset = CinemaHall.objects.all()
    serializer_class = CinemaHallSerializer
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    @extend_schema(
        description="Retrieve a list of cinema halls or create a new one"
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class MovieViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Movie.objects.prefetch_related("genres", "actors")
    serializer_class = MovieSerializer
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    def get_queryset(self):
        queryset = self.queryset
        params = self.request.query_params

        title = params.get("title")
        genres = params.get("genres")
        actors = params.get("actors")

        if title:
            queryset = queryset.filter(title__icontains=title)
        if genres:
            genre_ids = [int(g) for g in genres.split(",") if g.isdigit()]
            queryset = queryset.filter(genres__id__in=genre_ids)
        if actors:
            actor_ids = [int(a) for a in actors.split(",") if a.isdigit()]
            queryset = queryset.filter(actors__id__in=actor_ids)

        return queryset.distinct()

    def get_serializer_class(self):
        if self.action == "list":
            return MovieListSerializer
        if self.action == "retrieve":
            return MovieDetailSerializer
        return MovieSerializer

    @extend_schema(
        description="Retrieve a list of movies with optional filters",
        parameters=[
            OpenApiParameter(
                name="title",
                description="Filter movies by title (case-insensitive)",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="genres",
                description="Filter movies by genre IDs (comma-separated)",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="actors",
                description="Filter movies by actor IDs (comma-separated)",
                required=False,
                type=str,
            ),
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @action(
        methods=["POST"],
        detail=True,
        url_path="upload-image",
        permission_classes=[IsAdminUser],
    )
    @extend_schema(description="Upload a poster/image for a specific movie")
    def upload_image(self, request, pk=None):
        movie = self.get_object()
        serializer = MovieImageSerializer(movie, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    def get_serializer_class(self):
        if self.action == "list":
            return MovieSessionListSerializer
        if self.action == "retrieve":
            return MovieSessionDetailSerializer
        return MovieSessionSerializer

    def get_queryset(self):
        queryset = self.queryset
        date = self.request.query_params.get("date")
        movie = self.request.query_params.get("movie")

        if date:
            queryset = queryset.filter(show_time__date=date)
        if movie:
            queryset = queryset.filter(movie_id=movie)

        return queryset

    @extend_schema(
        description="Retrieve a list of movie sessions with optional filters",
        parameters=[
            OpenApiParameter(
                name="date",
                description="Filter sessions by date (format YYYY-MM-DD)",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="movie",
                description="Filter sessions by movie ID",
                required=False,
                type=int,
            ),
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class OrderPagination(PageNumberPagination):
    page_size = 10
    max_page_size = 100


class OrderViewSet(
    mixins.ListModelMixin, mixins.CreateModelMixin, GenericViewSet
):
    queryset = Order.objects.none()
    serializer_class = OrderSerializer
    pagination_class = OrderPagination
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return (
            Order.objects.filter(user=self.request.user)
            .prefetch_related(
                "tickets__movie_session__movie",
                "tickets__movie_session__cinema_hall",
            )
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
