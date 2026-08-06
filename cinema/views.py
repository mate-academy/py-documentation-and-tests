from datetime import datetime

from django.db.models import Count, F
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiParameter,
    extend_schema,
    extend_schema_view,
)
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

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


class GenreViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)


class ActorViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    queryset = Actor.objects.all()
    serializer_class = ActorSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)


class CinemaHallViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    queryset = CinemaHall.objects.all()
    serializer_class = CinemaHallSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter(
                name="title",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description=(
                    "Filter movies by a partial, "
                    "case-insensitive title match."
                ),
            ),
            OpenApiParameter(
                name="genres",
                type={
                    "type": "array",
                    "items": {"type": "integer"},
                },
                location=OpenApiParameter.QUERY,
                description=(
                    "Filter movies by genre IDs. "
                    "Pass IDs separated by commas, for example: 1,2."
                ),
                style="form",
                explode=False,
            ),
            OpenApiParameter(
                name="actors",
                type={
                    "type": "array",
                    "items": {"type": "integer"},
                },
                location=OpenApiParameter.QUERY,
                description=(
                    "Filter movies by actor IDs. "
                    "Pass IDs separated by commas, for example: 1,2."
                ),
                style="form",
                explode=False,
            ),
        ],
        description="Return a list of movies with optional filtering.",
    ),
    retrieve=extend_schema(
        description="Return detailed information about one movie.",
    ),
    create=extend_schema(
        description=(
            "Create a movie. Image uploading is not available through "
            "this endpoint. Use the upload-image endpoint instead."
        ),
    ),
)
class MovieViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    GenericViewSet,
):
    queryset = Movie.objects.prefetch_related("genres", "actors")
    serializer_class = MovieSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    @staticmethod
    def _params_to_ints(query_string):
        return [
            int(value)
            for value in query_string.split(",")
            if value
        ]

    def get_queryset(self):
        queryset = self.queryset

        title = self.request.query_params.get("title")
        genres = self.request.query_params.get("genres")
        actors = self.request.query_params.get("actors")

        if title:
            queryset = queryset.filter(title__icontains=title)

        if genres:
            genre_ids = self._params_to_ints(genres)
            queryset = queryset.filter(genres__id__in=genre_ids)

        if actors:
            actor_ids = self._params_to_ints(actors)
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

    @extend_schema(
        request=MovieImageSerializer,
        responses=MovieImageSerializer,
        description="Upload an image for a specific movie.",
    )
    @action(
        methods=["post"],
        detail=True,
        url_path="upload-image",
        permission_classes=[IsAdminUser],
    )
    def upload_image(self, request, pk=None):
        movie = self.get_object()
        serializer = self.get_serializer(
            movie,
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter(
                name="date",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description=(
                    "Filter movie sessions by show date. "
                    "Use the YYYY-MM-DD format."
                ),
            ),
            OpenApiParameter(
                name="movie",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter movie sessions by movie ID.",
            ),
        ],
        description=(
            "Return a list of movie sessions "
            "with optional date and movie filtering."
        ),
    ),
    retrieve=extend_schema(
        description="Return detailed information about one movie session.",
    ),
    create=extend_schema(
        description="Create a new movie session.",
    ),
    update=extend_schema(
        description="Replace an existing movie session.",
    ),
    partial_update=extend_schema(
        description="Partially update an existing movie session.",
    ),
    destroy=extend_schema(
        description="Delete an existing movie session.",
    ),
)
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
        queryset = self.queryset

        date_string = self.request.query_params.get("date")
        movie_id = self.request.query_params.get("movie")

        if date_string:
            date = datetime.strptime(
                date_string,
                "%Y-%m-%d",
            ).date()
            queryset = queryset.filter(show_time__date=date)

        if movie_id:
            queryset = queryset.filter(movie_id=int(movie_id))

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
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == "list":
            return OrderListSerializer

        return OrderSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
