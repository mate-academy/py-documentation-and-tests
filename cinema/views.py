from datetime import datetime

from django.db.models import Count, F
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework_simplejwt.authentication import JWTAuthentication

from cinema.models import (
    Actor,
    CinemaHall,
    Genre,
    Movie,
    MovieSession,
    Order,
)
from cinema.permissions import IsAdminOrIfAuthenticatedReadOnly
from cinema.serializers import (
    ActorSerializer,
    CinemaHallSerializer,
    GenreSerializer,
    MovieDetailSerializer,
    MovieImageSerializer,
    MovieListSerializer,
    MovieSerializer,
    MovieSessionDetailSerializer,
    MovieSessionListSerializer,
    MovieSessionSerializer,
    OrderListSerializer,
    OrderSerializer,
)


class GenreViewSet(mixins.CreateModelMixin,
                   mixins.ListModelMixin,
                   viewsets.GenericViewSet):
    """
    ViewSet for managing movie genres.
    Admin users can create, everyone can list.
    """
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)


class ActorViewSet(mixins.CreateModelMixin,
                   mixins.ListModelMixin,
                   viewsets.GenericViewSet):
    """
    ViewSet for managing actors.
    Admin users can create, everyone can list.
    """
    queryset = Actor.objects.all()
    serializer_class = ActorSerializer
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)


class CinemaHallViewSet(mixins.CreateModelMixin,
                        mixins.ListModelMixin,
                        viewsets.GenericViewSet):
    """
    ViewSet for managing cinema halls.
    Admin users can create, everyone can list.
    """
    queryset = CinemaHall.objects.all()
    serializer_class = CinemaHallSerializer
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)


@extend_schema(
    parameters=[
        OpenApiParameter(
            name="title",
            description="Filter movies by title",
            required=False,
            type=str,
        ),
        OpenApiParameter(
            name="genres",
            description="Filter movies by genre IDs (comma separated)",
            required=False,
            type=str,
        ),
        OpenApiParameter(
            name="actors",
            description="Filter movies by actor IDs (comma separated)",
            required=False,
            type=str,
        ),
    ]
)
class MovieViewSet(mixins.ListModelMixin,
                   mixins.CreateModelMixin,
                   mixins.RetrieveModelMixin,
                   viewsets.GenericViewSet):
    """
    ViewSet for movies. Supports list, create, retrieve, and image upload.
    """
    queryset = Movie.objects.prefetch_related("genres", "actors")
    serializer_class = MovieSerializer
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    @staticmethod
    def _params_to_ints(qs):
        """Convert a comma-separated string of IDs into a list of integers."""
        return [int(str_id) for str_id in qs.split(",")]

    def get_queryset(self):
        """Retrieve movies with optional filters: title, genres, actors."""
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
        """
        Upload an image for a specific movie.
        Only accessible to admin users.
        """
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
            type=str,
        ),
        OpenApiParameter(
            name="movie",
            description="Filter movie sessions by movie ID",
            required=False,
            type=int,
        ),
    ]
)
class MovieSessionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for movie sessions.
    Supports CRUD operations and filtering by date/movie.
    """
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
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    def get_queryset(self):
        """Retrieve movie sessions with optional filters: date, movie ID."""
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
    """Pagination for orders."""
    page_size = 10
    max_page_size = 100


class OrderViewSet(mixins.ListModelMixin,
                   mixins.CreateModelMixin,
                   viewsets.GenericViewSet):
    """
    ViewSet for orders.
    Supports listing and creating orders for authenticated users.
    """
    queryset = Order.objects.prefetch_related(
        "tickets__movie_session__movie", "tickets__movie_session__cinema_hall"
    )
    serializer_class = OrderSerializer
    pagination_class = OrderPagination
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        """Return orders for the current authenticated user."""
        return Order.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == "list":
            return OrderListSerializer
        return OrderSerializer

    def perform_create(self, serializer):
        """Save the order with the current authenticated user."""
        serializer.save(user=self.request.user)
