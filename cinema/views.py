# cinema/views.py

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    Actor,
    CinemaHall,
    Genre,
    Movie,
    MovieSession,
    Order,
)
from .permissions import IsAdminOrIfAuthenticatedReadOnly
from .serializers import (
    ActorSerializer,
    CinemaHallSerializer,
    GenreSerializer,
    MovieDetailSerializer,
    MovieImageSerializer,
    MovieListSerializer,
    MovieSessionDetailSerializer,
    MovieSessionListSerializer,
    OrderListSerializer,
    OrderSerializer,
)


class GenreViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)


class ActorViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Actor.objects.all()
    serializer_class = ActorSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)


class CinemaHallViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = CinemaHall.objects.all()
    serializer_class = CinemaHallSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)


class OrderPagination(PageNumberPagination):
    page_size = 10
    max_page_size = 100


@extend_schema(
    tags=["Movies"],
    summary="Operações com filmes",
    parameters=[
        OpenApiParameter(
            name="title",
            description="Filtro por título (case-insensitive, busca parcial).",
            required=False,
            type=str,
            location=OpenApiParameter.QUERY,
        ),
        OpenApiParameter(
            name="genres",
            description=(
                "Filtro por IDs de gêneros, separados por vírgula. "
                "Ex.: ?genres=1,2,5"
            ),
            required=False,
            type=str,
            location=OpenApiParameter.QUERY,
        ),
        OpenApiParameter(
            name="actors",
            description=(
                "Filtro por IDs de atores, separados por vírgula. "
                "Ex.: ?actors=3,7"
            ),
            required=False,
            type=str,
            location=OpenApiParameter.QUERY,
        ),
    ],
)
class MovieViewSet(viewsets.ModelViewSet):
    queryset = Movie.objects.prefetch_related("genres", "actors")
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)
    pagination_class = OrderPagination

    def get_serializer_class(self):
        if self.action == "list":
            return MovieListSerializer
        if self.action == "upload_image":
            return MovieImageSerializer
        return MovieDetailSerializer

    def get_queryset(self):
        queryset = self.queryset
        title = self.request.query_params.get("title")
        genres = self.request.query_params.get("genres")
        actors = self.request.query_params.get("actors")

        if title:
            queryset = queryset.filter(title__icontains=title)

        if genres:
            try:
                genre_ids = [
                    int(gid) for gid in genres.split(",") if gid.strip()
                ]
                queryset = queryset.filter(genres__id__in=genre_ids)
            except ValueError:
                pass

        if actors:
            try:
                actor_ids = [
                    int(aid) for aid in actors.split(",") if aid.strip()
                ]
                queryset = queryset.filter(actors__id__in=actor_ids)
            except ValueError:
                pass

        return queryset.distinct()

    @action(
        methods=["POST"],
        detail=True,
        url_path="upload-image",
        url_name="upload-image",
    )
    def upload_image(self, request, *args, **kwargs):
        """Faz upload de uma imagem para o filme."""
        movie = self.get_object()
        serializer = self.get_serializer(movie, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(
    tags=["Movie Sessions"],
    summary="Operações com sessões",
    parameters=[
        OpenApiParameter(
            name="date",
            description="Filtrar por data no formato YYYY-MM-DD.",
            required=False,
            type=str,
            location=OpenApiParameter.QUERY,
        ),
        OpenApiParameter(
            name="movie",
            description=(
                "Filtrar por id do filme (suporta múltiplos separados por "
                "vírgula). Ex.: ?movie=1,2"
            ),
            required=False,
            type=str,
            location=OpenApiParameter.QUERY,
        ),
    ],
)
class MovieSessionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MovieSession.objects.select_related("movie", "cinema_hall")
    pagination_class = OrderPagination

    def get_serializer_class(self):
        return (
            MovieSessionListSerializer
            if self.action == "list"
            else MovieSessionDetailSerializer
        )

    def get_queryset(self):
        qs = super().get_queryset()
        date_str = self.request.query_params.get("date")
        movie_ids_str = self.request.query_params.get("movie")

        if date_str:
            qs = qs.filter(show_time__date=date_str)

        if movie_ids_str:
            try:
                movie_ids = [
                    int(mid) for mid in movie_ids_str.split(",") if mid.strip()
                ]
                qs = qs.filter(movie_id__in=movie_ids)
            except ValueError:
                pass

        return qs


class OrderViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = OrderSerializer
    pagination_class = OrderPagination
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related(
            "tickets__movie_session__movie",
            "tickets__movie_session__cinema_hall",
        )

    def get_serializer_class(self):
        return (
            OrderListSerializer if self.action == "list" else OrderSerializer
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
