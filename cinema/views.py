from datetime import datetime
from typing import List, Type

from django.db.models import F, Count, QuerySet
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_view, extend_schema, \
    OpenApiParameter, OpenApiExample
from rest_framework import viewsets, mixins, status
from rest_framework.authentication import TokenAuthentication
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


@extend_schema_view(
    list=extend_schema(
        summary="List Genres",
        description="Retrieve a list of all the genres.",
        tags=["Genre"],
    ),
    create=extend_schema(
        summary="Create Genre",
        description="Create a new genre.",
        tags=["Genre"],
    ),
)
class GenreViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    """
    A viewset that provides `create` and `list` actions.
    This viewset is used to create and list Genre objects
    """
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)


@extend_schema_view(
    list=extend_schema(
        summary="List Actors",
        description="Retrieve a list of all the actors.",
        tags=["Actor"],
    ),
    create=extend_schema(
        summary="Create Actor",
        description="Create a new actor.",
        tags=["Actor"],
    ),
)
class ActorViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    """
    A viewset that provides `create` and `list` actions for Actor objects.
    This viewset is used to create and list Actor objects.
    """
    queryset = Actor.objects.all()
    serializer_class = ActorSerializer
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)


@extend_schema_view(
    list=extend_schema(
        summary="List Cinema Halls",
        description="Retrieve a list of all the cinema halls.",
        tags=["Cinema Hall"]
    ),
    create=extend_schema(
        summary="Create Cinema Hall",
        description="Create a new cinema hall.",
        tags=["Cinema Hall"],
    ),
)
class CinemaHallViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    """
    A viewset that provides `create` and `list` actions for CinemaHall objects.
    This viewset is used to create and list CinemaHall objects.
    """

    queryset = CinemaHall.objects.all()
    serializer_class = CinemaHallSerializer
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)


@extend_schema_view(
    list=extend_schema(
        summary="List Movies",
        description="Retrieve a list of movies with optional filters "
                    "for title, genres, and actors.",
        tags=["Movie"],
        parameters=[
            OpenApiParameter(
                name="title",
                type=OpenApiTypes.STR,
                description="Filter by movie title"
            ),
            OpenApiParameter(
                name="genres",
                type=OpenApiTypes.STR,
                description="Filter by genre IDs (comma-separated)"
            ),
            OpenApiParameter(
                name="actors",
                type=OpenApiTypes.STR,
                description="Filter by actor IDs (comma-separated)"
            )
        ]
    ),
    create=extend_schema(
        summary="Create Movie",
        description="Create a new movie.",
        tags=["Movie"],
    ),
    retrieve=extend_schema(
        summary="Retrieve Movie",
        description="Retrieve a specific movie by ID.",
        tags=["Movie"],
    )
)
class MovieViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    A viewset that provides `list`, `create`, and `retrieve` actions
    for Movie objects.
    This viewset is used to interact with Movie objects.
    """
    queryset = Movie.objects.prefetch_related("genres", "actors")
    serializer_class = MovieSerializer
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    @staticmethod
    def _params_to_ints(qs: str) -> List[int]:
        """Converts a list of string IDs to a list of integers"""
        return [int(str_id) for str_id in qs.split(",")]

    def get_queryset(self) -> QuerySet:
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

    def get_serializer_class(self) -> Type[
        MovieListSerializer
        | MovieDetailSerializer
        | MovieImageSerializer
        | MovieSerializer]:
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
    @extend_schema(
        summary="Upload Movie Image",
        description="Endpoint for uploading an image to a specific movie.",
        tags=["Movie"],
        responses={
            200: MovieImageSerializer,
            400: OpenApiTypes.OBJECT
        },
        examples=[
            OpenApiExample(
                "Successful response",
                summary="A successful response example",
                value={"image": "http://example.com/movies/1/image.jpg"}
            ),
            OpenApiExample(
                "Error response",
                summary="An error response example",
                value={"detail": "Invalid image upload."}
            )
        ]
    )
    def upload_image(self, request, pk=None) -> Response:
        """Endpoint for uploading image to specific movie"""
        movie = self.get_object()
        serializer = self.get_serializer(movie, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema_view(
    list=extend_schema(
        summary="List Movie Sessions",
        description="Retrieve a list of movie sessions with optional filters "
                    "for date and movie ID.",
        tags=["Movie Session"],
        parameters=[
            OpenApiParameter(
                name="date",
                type=OpenApiTypes.DATE,
                description="Filter by session date (YYYY-MM-DD)"
            ),
            OpenApiParameter(
                name="movie",
                type=OpenApiTypes.INT,
                description="Filter by movie ID"
            )
        ]
    ),
    create=extend_schema(
        summary="Create Movie Session",
        description="Create a new movie session.",
        request=MovieSessionSerializer,
        tags=["Movie Session"],
        responses={
            201: MovieSessionSerializer,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
        },
        examples=[
            OpenApiExample(
                "Successful response",
                summary="A successful response example",
                value={
                    "id": 1,
                    "movie": "Example Movie",
                    "cinema_hall": 1,
                    "show_time": "2024-06-30T18:00:00Z"
                }
            ),
            OpenApiExample(
                "Bad request response",
                summary="A bad request response example",
                value={
                    "show_time": ["This field is required."]
                }
            ),
            OpenApiExample(
                "Unauthorized response",
                summary="An unauthorized response example",
                value={
                    "detail": "Authentication credentials were not provided."
                }
            )
        ]
    ),
    retrieve=extend_schema(
        summary="Retrieve Movie Session Details",
        description="Retrieve details of a specific movie session by ID.",
        tags=["Movie Session"],
    ),
    update=extend_schema(
        summary="Update Movie Session",
        description="Update an existing movie session by ID.",
        request=MovieSessionSerializer,
        tags=["Movie Session"],
        responses={
            200: MovieSessionSerializer,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
        },
        examples=[
            OpenApiExample(
                "Successful response",
                summary="A successful response example",
                value={
                    "id": 1,
                    "movie": "Example Movie",
                    "cinema_hall": 1,
                    "show_time": "2024-06-30T20:00:00Z"
                }
            ),
            OpenApiExample(
                "Bad request response",
                summary="A bad request response example",
                value={
                    "show_time": ["Invalid date format."]
                }
            ),
            OpenApiExample(
                "Unauthorized response",
                summary="An unauthorized response example",
                value={
                    "detail": "Authentication credentials were not provided."
                }
            )
        ]
    ),
    partial_update=extend_schema(
        summary="Partially Update Movie Session",
        description="Partially update an existing movie session by ID.",
        request=MovieSessionSerializer,
        tags=["Movie Session"],
        responses={
            200: MovieSessionSerializer,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
        },
        examples=[
            OpenApiExample(
                "Successful response",
                summary="A successful response example",
                value={
                    "id": 1,
                    "movie": "Example Movie",
                    "cinema_hall": 1,
                    "show_time": "2024-06-30T19:00:00Z"
                }
            ),
            OpenApiExample(
                "Bad request response",
                summary="A bad request response example",
                value={
                    "show_time": ["Invalid date format."]
                }
            ),
            OpenApiExample(
                "Unauthorized response",
                summary="An unauthorized response example",
                value={
                    "detail": "Authentication credentials were not provided."
                }
            )
        ]
    ),
    destroy=extend_schema(
        summary="Delete Movie Session",
        description="Delete an existing movie session by ID.",
        tags=["Movie Session"],
        responses={
            204: None,
            401: OpenApiTypes.OBJECT,
        },
        examples=[
            OpenApiExample(
                "Successful response",
                summary="A successful response example",
                value=None
            ),
            OpenApiExample(
                "Unauthorized response",
                summary="An unauthorized response example",
                value={
                    "detail": "Authentication credentials were not provided."
                }
            )
        ]
    )
)
class MovieSessionViewSet(viewsets.ModelViewSet):
    """
    A viewset for handling Movie Sessions.
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
        summary="List Orders",
        description="Retrieve a list of orders placed by "
                    "the authenticated user.",
        tags=["Orders"]
    ),
    create=extend_schema(
        summary="Create Order",
        description="Create a new order with tickets.",
        request=OrderSerializer,
        responses={
            201: OrderSerializer,
            400: "Bad Request",
            401: "Unauthorized"
        },
        examples=[
            OpenApiExample(
                "Successful Response",
                summary="A successful response example",
                value={
                    "id": 1,
                    "tickets": [
                        {
                            "row": 1,
                            "seat": 1,
                            "movie_session": 1,
                        }
                    ],
                    "created_at": "2024-06-30T12:00:00Z"
                }
            ),
            OpenApiExample(
                "Bad Request Response",
                summary="A bad request response example",
                value={
                    "tickets": ["This field is required."]
                }
            ),
            OpenApiExample(
                "Unauthorized Response",
                summary="An unauthorized response example",
                value={
                    "detail": "Authentication credentials were not provided."
                }
            )
        ],
        tags=["Orders"]
    )
)
class OrderViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    GenericViewSet,
):
    """
    Viewset for Order model.
    This viewset provides list and create actions for Order model.
    """
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
