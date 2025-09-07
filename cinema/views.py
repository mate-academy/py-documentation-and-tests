from datetime import datetime

from django.db.models import F, Count
from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.pagination import (PageNumberPagination)
from rest_framework.permissions import (IsAuthenticated,
                                        IsAdminUser)
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework.parsers import (MultiPartParser,
                                    FormParser)
from rest_framework_simplejwt.authentication import (
    JWTAuthentication)

from drf_spectacular.utils import (extend_schema,
                                   OpenApiParameter)
from drf_spectacular.types import OpenApiTypes

from cinema.models import (
    Genre,
    Actor,
    CinemaHall,
    Movie,
    MovieSession,
    Order,
)
from cinema.permissions import IsAdminOrIfAuthenticatedReadOnly
from cinema.serializers import (
    GenreSerializer,
    ActorSerializer,
    CinemaHallSerializer,
    MovieSerializer,
    MovieCreateSerializer,
    MovieListSerializer,
    MovieDetailSerializer,
    MovieImageSerializer,
    MovieSessionSerializer,
    MovieSessionListSerializer,
    MovieSessionDetailSerializer,
    OrderSerializer,
    OrderListSerializer,
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


class ActorViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    queryset = Actor.objects.all()
    serializer_class = ActorSerializer
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)


class CinemaHallViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    queryset = CinemaHall.objects.all()
    serializer_class = CinemaHallSerializer
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)


@extend_schema(
    parameters=[
        OpenApiParameter(
            name="title",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description="Case-insensitive substring for title.",
        ),
        OpenApiParameter(
            name="genres",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description="Genre IDs comma-separated, e.g. '1,2,5'.",
        ),
        OpenApiParameter(
            name="actors",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description="Actor IDs comma-separated, e.g. '3,4'.",
        ),
    ]
)
class MovieViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,      # оновлення
    mixins.DestroyModelMixin,     # видалення
    viewsets.GenericViewSet,
):
    queryset = Movie.objects.prefetch_related("genres", "actors")
    serializer_class = MovieSerializer
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    @staticmethod
    def _params_to_ints(qs: str) -> list[int]:
        return [int(item) for item in qs.split(",")
                if item.strip()]

    def get_queryset(self):
        title = self.request.query_params.get("title")
        genres = self.request.query_params.get("genres")
        actors = self.request.query_params.get("actors")

        queryset = self.queryset

        if title:
            queryset = queryset.filter(title__icontains=title)
        if genres:
            ids = self._params_to_ints(genres)
            queryset = queryset.filter(genres__id__in=ids)
        if actors:
            ids = self._params_to_ints(actors)
            queryset = queryset.filter(actors__id__in=ids)

        return queryset.distinct()

    def get_serializer_class(self):
        if self.action == "list":
            return MovieListSerializer
        if self.action == "retrieve":
            return MovieDetailSerializer
        if self.action == "upload_image":
            return MovieImageSerializer
        if self.action in ("create", "update", "partial_update"):
            return MovieCreateSerializer
        return MovieSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data,
                                         partial=True)
        serializer.is_valid(raise_exception=True)
        vdata = dict(serializer.validated_data)

        # Ігноруємо image повністю під час створення
        vdata.pop("image", None)

        # Витягуємо M2M
        genres = vdata.pop("genres", [])
        actors = vdata.pop("actors", [])

        # Створюємо об'єкт з image=None
        movie = Movie.objects.create(image=None, **vdata)

        if genres:
            movie.genres.set(genres)
        if actors:
            movie.actors.set(actors)

        out = self.get_serializer(movie)
        headers = self.get_success_headers(out.data)
        return Response(out.data, status=status.HTTP_201_CREATED,
                        headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.get("partial", False)
        instance = self.get_object()

        data = request.data.copy()
        # ігноруємо image у PATCH/PUT, щоб картинка змінювалась тільки через upload-image
        data.pop("image", None)

        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    @action(
        methods=["POST"],
        detail=True,
        url_path="upload-image",
        permission_classes=[IsAdminUser],
        parser_classes=[MultiPartParser, FormParser],  # ✅ лише тут multipart
    )
    def upload_image(self, request, pk=None):
        """Upload image to specific movie."""
        if "image" not in request.FILES:
            return Response(
                {"image": ["This field is required."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

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
            type=OpenApiTypes.DATE,
            location=OpenApiParameter.QUERY,
            description="Filter by show_time date (YYYY-MM-DD).",
        ),
        OpenApiParameter(
            name="movie",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description="Filter by movie ID.",
        ),
    ]
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
            date_obj = datetime.strptime(date, "%Y-%m-%d").date()
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
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == "list":
            return OrderListSerializer
        return OrderSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
