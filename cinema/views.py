from datetime import datetime
from typing import List, Type

from django.db.models import Count, F, QuerySet
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.request import Request
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
from cinema.serializers import (
    ActorSerializer,
    CinemaHallSerializer,
    GenreSerializer,
    MovieBaseSerializer,
    MovieDetailSerializer,
    MovieImageSerializer,
    MovieListSerializer,
    MovieSessionBaseSerializer,
    MovieSessionDetailSerializer,
    MovieSessionListSerializer,
    OrderBaseSerializer,
    OrderListSerializer,
)


class BaseModelViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    """Base ViewSet with common functionality"""

    pass


class GenreViewSet(BaseModelViewSet):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer


class ActorViewSet(BaseModelViewSet):
    queryset = Actor.objects.all()
    serializer_class = ActorSerializer


class CinemaHallViewSet(BaseModelViewSet):
    queryset = CinemaHall.objects.all()
    serializer_class = CinemaHallSerializer


class MovieViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Movie.objects.prefetch_related("genres", "actors")
    serializer_class = MovieBaseSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "title",
                type=OpenApiTypes.STR,
                description="Filter by movie title (ex. ?title=Inception)",
            ),
            OpenApiParameter(
                "genres",
                type=OpenApiTypes.STR,
                description=(
                    "Filter by genre ids. Multiple ids can be separated "
                    "by commas (ex. ?genres=1,2)"
                ),
            ),
            OpenApiParameter(
                "actors",
                type=OpenApiTypes.STR,
                description=(
                    "Filter by actor ids. Multiple ids can be separated "
                    "by commas (ex. ?actors=1,2)"
                ),
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @staticmethod
    def _params_to_ints(ids_string: str) -> List[int]:
        """Converts a list of string IDs to a list of integers"""
        return [int(str_id) for str_id in ids_string.split(",")]

    def get_queryset(self) -> QuerySet[Movie]:
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

    def get_serializer_class(self) -> Type[serializers.ModelSerializer]:
        if self.action == "list":
            return MovieListSerializer

        if self.action == "retrieve":
            return MovieDetailSerializer

        if self.action == "upload_image":
            return MovieImageSerializer

        return MovieBaseSerializer

    @extend_schema(
        description="Upload movie image",
        request=MovieImageSerializer,
        responses={200: MovieImageSerializer},
    )
    @action(
        methods=["POST"],
        detail=True,
        url_path="upload-image",
        permission_classes=[IsAdminUser],
    )
    def upload_image(self, request: Request, pk: int = None):
        """Endpoint for uploading image to specific movie"""
        movie = self.get_object()
        serializer = self.get_serializer(movie, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


class MovieSessionViewSet(viewsets.ModelViewSet):
    queryset = MovieSession.objects.select_related(
        "movie", "cinema_hall"
    ).annotate(
        tickets_available=(
            F("cinema_hall__rows") * F("cinema_hall__seats_in_row")
            - Count("tickets")
        )
    )
    serializer_class = MovieSessionBaseSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "date",
                type=OpenApiTypes.DATE,
                description="Filter by show date (ex. ?date=2024-12-25)",
            ),
            OpenApiParameter(
                "movie",
                type=OpenApiTypes.INT,
                description="Filter by movie id (ex. ?movie=1)",
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self) -> QuerySet[MovieSession]:
        date = self.request.query_params.get("date")
        movie_id_str = self.request.query_params.get("movie")

        queryset = self.queryset

        if date:
            date = datetime.strptime(date, "%Y-%m-%d").date()
            queryset = queryset.filter(show_time__date=date)

        if movie_id_str:
            queryset = queryset.filter(movie_id=int(movie_id_str))

        return queryset

    def get_serializer_class(self) -> Type[serializers.ModelSerializer]:
        if self.action == "list":
            return MovieSessionListSerializer

        if self.action == "retrieve":
            return MovieSessionDetailSerializer

        return MovieSessionBaseSerializer


class OrderViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    GenericViewSet,
):
    queryset = Order.objects.prefetch_related(
        "tickets__movie_session__movie", "tickets__movie_session__cinema_hall"
    )
    serializer_class = OrderBaseSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self) -> QuerySet[Order]:
        return self.queryset.filter(user=self.request.user)

    def get_serializer_class(self) -> Type[serializers.ModelSerializer]:
        if self.action == "list":
            return OrderListSerializer

        return OrderBaseSerializer

    def perform_create(self, serializer: OrderBaseSerializer) -> None:
        serializer.save(user=self.request.user)
