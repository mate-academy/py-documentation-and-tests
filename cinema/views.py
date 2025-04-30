from datetime import datetime

from django.db.models import F, Count
from rest_framework import viewsets, mixins, status
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    extend_schema_view,
)

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


@extend_schema(
    summary="List or create genres",
    description="Authenticated users can list genres. Only admins can "
                "create new ones.",
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
    summary="List or create actors",
    description="Authenticated users can list actors. "
                "Only admins can create new ones.",
)
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
        summary="List actors",
        description="Returns a list of all actors. "
                    "Only available to authenticated users.",
        responses={200: ActorSerializer(many=True)},
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Create actor",
        description="Creates a new actor. Only available to admin users.",
        responses={201: ActorSerializer},
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)


@extend_schema(
    summary="List or create cinema halls",
    description="Authenticated users can list cinema halls. "
                "Only admins can create new ones.",
)
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
        summary="List cinema halls",
        description="Returns a list of all cinema halls. "
                    "Available to any authenticated user.",
        responses={200: CinemaHallSerializer(many=True)},
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Create a cinema hall",
        description="Creates a new cinema hall. "
                    "Only available to admin users.",
        responses={201: CinemaHallSerializer},
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)


@extend_schema(
    summary="List, retrieve, or create movies",
    description="Supports filtering by title, genres, and actors. "
                "dmins can create and upload images.",
)
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
        summary="List movies",
        description="Returns a list of movies. Supports filtering by "
                    "title, genres, and actors.",
        parameters=[
            OpenApiParameter(
                name="title",
                description="Filter by movie title (partial match)",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="genres",
                description="Comma-separated genre IDs (e.g., 1,2,3)",
                required=False,
                type={
                    "type": "array",
                    "items": {"type": "integer"},
                    "style": "form",
                },
            ),
            OpenApiParameter(
                name="actors",
                description="Comma-separated actor IDs (e.g., 4,5)",
                required=False,
                type={
                    "type": "array",
                    "items": {"type": "integer"},
                    "style": "form",
                },
            ),
        ],
        responses={200: MovieListSerializer(many=True)},
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Retrieve a movie",
        description="Get detailed information about a specific movie "
                    "by its ID.",
        responses={200: MovieDetailSerializer},
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Create a movie",
        description="Create a new movie entry. "
                    "Only accessible by admin users.",
        responses={201: MovieSerializer},
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Upload an image to a movie",
        description="Upload an image for a specific movie. "
                    "Only admins can perform this action.",
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


@extend_schema_view(
    list=extend_schema(
        summary="List movie sessions",
        description="Retrieve a list of movie sessions. Supports filtering by "
                    "session date (YYYY-MM-DD) and movie ID.",
        parameters=[
            OpenApiParameter(
                name="date",
                description="Filter by session date (YYYY-MM-DD)",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="movie",
                description="Filter by movie ID",
                required=False,
                type=int,
            ),
        ],
        responses={200: MovieSessionListSerializer(many=True)},
    ),
    retrieve=extend_schema(
        summary="Retrieve a movie session",
        description="Get detailed information about a specific movie session.",
        responses={200: MovieSessionDetailSerializer},
    ),
    create=extend_schema(
        summary="Create a movie session",
        description="Admin users can create new movie sessions by specifying "
                    "movie, cinema hall, and show time.",
        request=MovieSessionSerializer,
        responses={201: MovieSessionSerializer},
    ),
    update=extend_schema(
        summary="Update a movie session",
        description="Completely update an existing movie session. Admin only.",
        request=MovieSessionSerializer,
        responses={200: MovieSessionSerializer},
    ),
    partial_update=extend_schema(
        summary="Partially update a movie session",
        description="Update selected fields of a movie session. Admin only.",
        request=MovieSessionSerializer,
        responses={200: MovieSessionSerializer},
    ),
    destroy=extend_schema(
        summary="Delete a movie session",
        description="Delete a movie session by ID. Admin only.",
        responses={204: None},
    ),
)
@extend_schema(
    summary="List, retrieve, or manage movie sessions",
    description="Supports filtering by date (YYYY-MM-DD) and movie ID.",
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


class OrderPagination(PageNumberPagination):
    page_size = 10
    max_page_size = 100


@extend_schema_view(
    list=extend_schema(
        summary="List user's orders",
        description="Retrieve a list of orders made by the authenticated user."
                    " Each order includes related ticket and movie session "
                    "information.",
        responses={200: OrderListSerializer(many=True)},
    ),
    create=extend_schema(
        summary="Create a new order",
        description="Create a new order for the authenticated user. The order "
                    "must include valid ticket data.",
        request=OrderSerializer,
        responses={201: OrderSerializer},
    ),
)
@extend_schema(
    summary="List or create orders",
    description="Authenticated users can create orders and view their own "
                "order history. Admins are not required.",
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
