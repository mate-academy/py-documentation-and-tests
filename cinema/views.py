from datetime import datetime

from django.db.models import F, Count
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    extend_schema,
    OpenApiResponse,
    OpenApiParameter
)
from rest_framework import (
    viewsets,
    mixins,
    status
)
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
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
        summary="Create genre",
        description="Create new genre",
        request=GenreSerializer,
        responses={
            201: GenreSerializer,
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Unauthorized")
        },
        tags=["genre"],
    )
    def create(self, request, *args, **kwargs):
        """Creates new genre"""
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="List of genres",
        description="Returns list of all genres",
        request=GenreSerializer,
        responses={
            200: GenreSerializer,
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Unauthorized")
        },
        tags=["genre"],
    )
    def list(self, request, *args, **kwargs):
        """Returns list of genres"""
        return super().list(request, *args, **kwargs)


class ActorViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    queryset = Actor.objects.all()
    serializer_class = ActorSerializer

    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    @extend_schema(
        summary="Create actor",
        description="Create new actor",
        request=ActorSerializer,
        responses={
            201: ActorSerializer,
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Unauthorized")
        },
        tags=["actor"],
    )
    def create(self, request, *args, **kwargs):
        """Creates new actor"""
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="List of actors",
        description="Returns list of all actors",
        request=ActorSerializer,
        responses={
            200: ActorSerializer,
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Unauthorized")
        },
        tags=["actor"],
    )
    def list(self, request, *args, **kwargs):
        """Returns list of actors"""
        return super().list(request, *args, **kwargs)


class CinemaHallViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    queryset = CinemaHall.objects.all()
    serializer_class = CinemaHallSerializer

    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    @extend_schema(
        summary="Create cinema hall",
        description="Create new cinema hall",
        request=CinemaHallSerializer,
        responses={
            201: CinemaHallSerializer,
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Unauthorized")
        },
        tags=["cinema hall"],
    )
    def create(self, request, *args, **kwargs):
        """Creates new cinema hall"""
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="List of cinema halls",
        description="Returns list of all cinema halls",
        request=CinemaHallSerializer,
        responses={
            200: CinemaHallSerializer,
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Unauthorized")
        },
        tags=["cinema hall"],
    )
    def list(self, request, *args, **kwargs):
        """Returns list of cinema halls"""
        return super().list(request, *args, **kwargs)


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
        summary="Returns movie",
        description="Returns specific movie",
        request=MovieDetailSerializer,
        responses={
            200: MovieDetailSerializer,
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Unauthorized")
        },
        tags=["movie"],
    )
    def retrieve(self, request, *args, **kwargs):
        """Get specific movie"""
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Upload image",
        description="Uploads image to specific movie",
        request=MovieImageSerializer,
        responses={
            200: MovieImageSerializer,
            400: OpenApiResponse(description="Bad request"),
        },
        tags=["movie"],
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
        summary="Create movie",
        description="Create new movie",
        request=MovieSerializer,
        responses={
            201: MovieSerializer,
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Unauthorized")
        },
        tags=["movie"],
    )
    def create(self, request, *args, **kwargs):
        """Creates new movie"""
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="List of movies",
        description="Returns list of all movies",
        responses={
            200: MovieListSerializer,
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Unauthorized")
        },
        tags=["movie"],
        parameters=[
            OpenApiParameter(
                "title",
                type=str,
                description="Filter by title of movie",
                required=False,
                explode=False,
            ),
            OpenApiParameter(
                "genres",
                type={"type": "array", "items": {"type": "integer"}},
                description="Filter by genre of movie",
                required=False,
                many=True,
                explode=False,
            ),
            OpenApiParameter(
                name="actors",
                type={"type": "array", "items": {"type": "integer"}},
                description="Filter by actors",
                required=False,
                many=True,
                explode=False,
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        """Returns list of movies"""
        return super().list(request, *args, **kwargs)


class MovieSessionViewSet(viewsets.ModelViewSet):
    queryset = (
        MovieSession.objects.all()
        .select_related("movie", "cinema_hall")
        .annotate(
            tickets_available=(
                F("cinema_hall__rows")
                * F("cinema_hall__seats_in_row")
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
        summary="Delete movie session",
        description="Remove specific movie session.",
        responses={
            204: MovieSessionSerializer,
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Unauthorized")
        },
        tags=["movie session"],
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @extend_schema(
        summary="Partial update movie session",
        description="Partially updates specific movie session.",
        responses={
            200: MovieSessionSerializer,
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Unauthorized")
        },
        tags=["movie session"],
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Update movie session",
        description="Updates specific movie session.",
        responses={
            200: MovieSessionSerializer,
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Unauthorized")
        },
        tags=["movie session"],
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Get movie session",
        description="Get specific movie session.",
        responses={
            200: MovieSessionDetailSerializer,
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Unauthorized")
        },
        tags=["movie session"],
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Create movie session",
        description="Create new movie session.",
        responses={
            201: MovieSessionSerializer,
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Unauthorized")
        },
        tags=["movie session"],
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="List movie session",
        description="List of all movie session",
        responses={
            200: MovieSessionListSerializer,
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Unauthorized")
        },
        tags=["movie session"],
        parameters=[
            OpenApiParameter(
                "date",
                type=OpenApiTypes.DATE,
                description="Filter by date (e.g. 2024-10-25)",
                required=False,
            ),
            OpenApiParameter(
                "movie",
                type=OpenApiTypes.INT,
                description="Filter by movie ID",
                required=False,
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
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
        summary="Create order",
        description="Create new order",
        request=OrderSerializer,
        responses={
            201: OrderSerializer,
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Unauthorized")
        },
        tags=["order"],
    )
    def create(self, request, *args, **kwargs):
        """Creates new order"""
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="List of orders",
        description="Returns list of all orders",
        request=OrderListSerializer,
        responses={
            200: OrderListSerializer,
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Unauthorized")
        },
        tags=["order"],
    )
    def list(self, request, *args, **kwargs):
        """Returns list of orders"""
        return super().list(request, *args, **kwargs)
