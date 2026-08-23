from datetime import datetime

from django.db.models import F, Count
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from rest_framework import viewsets, mixins, status
from rest_framework_simplejwt.authentication import JWTAuthentication
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


@extend_schema_view(
    list=extend_schema(
        summary="List genres",
        description="Retrieve a list of all movie genres.",
        responses=GenreSerializer,
    ),
    create=extend_schema(
        summary="Create genre",
        description="Create a new movie genre. Available to administrators.",
        request=GenreSerializer,
        responses=GenreSerializer,
    ),
)
class GenreViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)


@extend_schema_view(
    list=extend_schema(
        summary="List actors",
        description="Retrieve a list of all actors.",
        responses=ActorSerializer,
    ),
    create=extend_schema(
        summary="Create actor",
        description="Create a new actor. Available to administrators.",
        request=ActorSerializer,
        responses=ActorSerializer,
    ),
)
class ActorViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    queryset = Actor.objects.all()
    serializer_class = ActorSerializer
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)


@extend_schema_view(
    list=extend_schema(
        summary="List cinema halls",
        description="Retrieve a list of all cinema halls.",
        responses=CinemaHallSerializer,
    ),
    create=extend_schema(
        summary="Create cinema hall",
        description="Create a new cinema hall. Available to administrators.",
        request=CinemaHallSerializer,
        responses=CinemaHallSerializer,
    ),
)
class CinemaHallViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    queryset = CinemaHall.objects.all()
    serializer_class = CinemaHallSerializer
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)


@extend_schema_view(
    list=extend_schema(
        summary="List movies",
        description=(
            "Retrieve a list of movies. Movies can be filtered "
            "by title, genre IDs, and actor IDs."
        ),
        parameters=[
            OpenApiParameter(
                name="title",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter movies by title.",
                required=False,
            ),
            OpenApiParameter(
                name="genres",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description=(
                    "Filter movies by genre IDs. "
                    "Multiple IDs can be separated by commas."
                ),
                required=False,
            ),
            OpenApiParameter(
                name="actors",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description=(
                    "Filter movies by actor IDs. "
                    "Multiple IDs can be separated by commas."
                ),
                required=False,
            ),
        ],
        responses=MovieListSerializer,
    ),
    create=extend_schema(
        summary="Create movie",
        description="Create a new movie. Available to administrators.",
        request=MovieSerializer,
        responses=MovieSerializer,
    ),
    retrieve=extend_schema(
        summary="Retrieve movie",
        description="Retrieve detailed information about a specific movie.",
        responses=MovieDetailSerializer,
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
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    @staticmethod
    def _params_to_ints(qs):
        """Converts a list of string IDs to a list of integers."""
        return [int(str_id) for str_id in qs.split(",")]

    def get_queryset(self):
        """Retrieve the movies with filters."""
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

    @extend_schema(
        summary="Upload movie image",
        description="Upload or replace the image of a specific movie.",
        request=MovieImageSerializer,
        responses=MovieImageSerializer,
    )
    @action(
        methods=["POST"],
        detail=True,
        url_path="upload-image",
        permission_classes=[IsAdminUser],
    )
    def upload_image(self, request, pk=None):
        """Endpoint for uploading image to specific movie."""
        movie = self.get_object()
        serializer = self.get_serializer(movie, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(
                serializer.data,
                status=status.HTTP_200_OK,
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )

    def get_serializer_class(self):
        if self.action == "list":
            return MovieListSerializer

        if self.action == "retrieve":
            return MovieDetailSerializer

        if self.action == "upload_image":
            return MovieImageSerializer

        return MovieSerializer


@extend_schema_view(
    list=extend_schema(
        summary="List movie sessions",
        description=(
            "Retrieve a list of movie sessions. "
            "Sessions can be filtered by date and movie."
        ),
        parameters=[
            OpenApiParameter(
                name="date",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description="Filter movie sessions by date.",
                required=False,
            ),
            OpenApiParameter(
                name="movie",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter movie sessions by movie ID.",
                required=False,
            ),
        ],
        responses=MovieSessionListSerializer,
    ),
    create=extend_schema(
        summary="Create movie session",
        description=(
            "Create a new movie session. "
            "Available to administrators."
        ),
        request=MovieSessionSerializer,
        responses=MovieSessionSerializer,
    ),
    retrieve=extend_schema(
        summary="Retrieve movie session",
        description="Retrieve detailed information about a movie session.",
        responses=MovieSessionDetailSerializer,
    ),
    update=extend_schema(
        summary="Update movie session",
        description="Update all fields of an existing movie session.",
        request=MovieSessionSerializer,
        responses=MovieSessionSerializer,
    ),
    partial_update=extend_schema(
        summary="Partially update movie session",
        description="Update selected fields of an existing movie session.",
        request=MovieSessionSerializer,
        responses=MovieSessionSerializer,
    ),
    destroy=extend_schema(
        summary="Delete movie session",
        description="Delete an existing movie session.",
        responses=None,
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
    authentication_classes = (JWTAuthentication,)
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
        summary="List user orders",
        description=(
            "Retrieve a paginated list of orders "
            "belonging to the authenticated user."
        ),
        responses=OrderListSerializer,
    ),
    create=extend_schema(
        summary="Create order",
        description=(
            "Create a new order for the authenticated user."
        ),
        request=OrderSerializer,
        responses=OrderSerializer,
    ),
)
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
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return Order.objects.filter(
            user=self.request.user
        )

    def get_serializer_class(self):
        if self.action == "list":
            return OrderListSerializer

        return OrderSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
