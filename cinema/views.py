from datetime import datetime

from django.db.models import F, Count
from rest_framework import viewsets, mixins, status
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ReadOnlyModelViewSet
from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiExample
)
from drf_spectacular.types import OpenApiTypes

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
        summary="Get list of genres",
        examples=[
            OpenApiExample(
                "1",
                response_only=True,
                value=[
                    {
                        "id": 1,
                        "name": "Crime"
                    },
                    {
                        "...": "..."
                    },
                ]
            )
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Create a genre",
        examples=[
            OpenApiExample(
                "Request body",
                value={
                    "name": "Crime"
                },
                request_only=True,
            ),
            OpenApiExample(
                "Response",
                value={
                    "id": 1,
                    "name": "Crime"
                },
                response_only=True,
            )
        ],
    )
    def create(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


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
        summary="Get list of actors",
        examples=[
            OpenApiExample(
                "1",
                response_only=True,
                value=[
                    {
                        "id": 1,
                        "first_name": "Tom",
                        "last_name": "Hanks",
                        "full_name": "Tom Hanks"
                    },
                    {
                        "...": "..."
                    },
                ]
            )
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Create an actor",
        examples=[
            OpenApiExample(
                "Request body",
                value={
                    "first_name": "Tom",
                    "last_name": "Hanks",
                },
                request_only=True,
            ),
            OpenApiExample(
                "Response",
                value={
                    "id": 1,
                    "first_name": "Tom",
                    "last_name": "Hanks",
                    "full_name": "Tom Hanks"
                },
                response_only=True,
            )
        ],
    )
    def create(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


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
        summary="Get list of cinema halls",
        examples=[
            OpenApiExample(
                "1",
                response_only=True,
                value=[
                    {
                        "id": 1,
                        "name": "Ricciotto Canudo",
                        "rows": 25,
                        "seats_in_row": 30,
                        "capacity": 750
                    },
                    {
                        "...": "..."
                    },
                ]
            )
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Create an actor",
        examples=[
            OpenApiExample(
                "Request body",
                value={
                    "name": "Robin Wood",
                    "rows": 24,
                    "seats_in_row": 18
                },
                request_only=True,
            ),
            OpenApiExample(
                "Response",
                value={
                    "id": 1,
                    "name": "Robin Wood",
                    "rows": 24,
                    "seats_in_row": 18,
                    "capacity": 432
                },
                response_only=True,
            )
        ],
    )
    def create(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


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
        summary="Upload an image",
        request={
            "multipart/form-data": {
                "type": "object",
                "properties": {
                    "image": {
                        "type": "string",
                        "format": "binary",
                    }
                },
                "required": ["image"],
            }
        },
        examples=[
            OpenApiExample(
                name="Response body",
                value={
                    "id": 1,
                    "image": "Image URL"
                },
                response_only=True,
                media_type="application/json",
            )
        ],
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
        summary="Get list of movies",
        parameters=[
            OpenApiParameter(
                name="title",
                description="Filter by movie title",
                required=False,
                type=OpenApiTypes.STR,
            ),
            OpenApiParameter(
                name="genres",
                description="Filter by genres",
                required=False,
                type=OpenApiTypes.STR,
            ),
            OpenApiParameter(
                name="actors",
                description="Filter by actors",
                required=False,
                type=OpenApiTypes.STR,
            )
        ],
        examples=[
            OpenApiExample(
                "1",
                response_only=True,
                value=[
                    {
                        "id": 1,
                        "title": "The Departed",
                        "description": "An undercover cop and a mole in the"
                                       " police attempt to identify each other"
                                       " while infiltrating an Irishgang in"
                                       " South Boston.",
                        "duration": 151,
                        "genres": [
                            "Crime",
                            "Drama",
                            "Thriller"
                        ],
                        "actors": [
                            "Jack Nicholson",
                            "Leonardo DiCaprio",
                            "Matt Damon"
                        ],
                        "image": None
                    },
                    {
                        "...": "..."
                    },
                ]
            )
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Create a movie session",
        examples=[
            OpenApiExample(
                name="Request body",
                value={
                    "title": "string",
                    "description": "string",
                    "duration": 148,
                    "genres": [1, 2, 3],
                    "actors": [1, 2, 3]
                },
                request_only=True
            ),
            OpenApiExample(
                name="Response body",
                value={
                    "id": 2,
                    "title": "string",
                    "description": "string",
                    "duration": 148,
                    "genres": [
                        "Crime",
                        "Drama",
                        "Thriller"
                    ],
                    "actors": [
                        "Leonardo DiCaprio",
                        "Joseph Gordon-Levitt",
                        "Elliot Page"
                    ],
                    "image": None
                },
                response_only=True
            )
        ]
    )
    def create(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Movie detail view",
        examples=[
            OpenApiExample(
                name="Response body",
                response_only=True,
                value={
                    "id": 1,
                    "title": "The Departed",
                    "description": "An undercover cop and a mole in the"
                                   " police attempt to identify each other"
                                   " while infiltrating an Irishgang in"
                                   " South Boston.",
                    "duration": 151,
                    "genres": [
                        {
                            "id": 1,
                            "name": "Crime"
                        },
                        {
                            "id": 2,
                            "name": "Drama"
                        },
                        {
                            "id": 3,
                            "name": "Thriller"
                        }
                    ],
                    "actors": [
                        {
                            "id": 1,
                            "first_name": "Jack",
                            "last_name": "Nicholson",
                            "full_name": "Jack Nicholson"
                        },
                        {
                            "id": 2,
                            "first_name": "Leonardo",
                            "last_name": "DiCaprio",
                            "full_name": "Leonardo DiCaprio"
                        },
                        {
                            "id": 3,
                            "first_name": "Matt",
                            "last_name": "Damon",
                            "full_name": "Matt Damon"
                        }
                    ],
                    "image": None
                }
            )
        ]
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)


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

    @extend_schema(
        summary="Get list of movie sessions",
        parameters=[
            OpenApiParameter(
                name="date",
                description="Filter by date of the movie session",
                required=False,
                type=OpenApiTypes.DATE,
                pattern=r"^\d{4}-\d{2}-\d{2}$",
            ),
            OpenApiParameter(
                name="movie",
                description="Filter by movie id",
                required=False,
                type=OpenApiTypes.STR,
            )
        ],
        examples=[
            OpenApiExample(
                "1",
                value=[
                    {
                        "id": 1,
                        "show_time": "2024-10-08T13:00:00Z",
                        "movie_title": "The Departed",
                        "movie_image": None,
                        "cinema_hall_name": "Ricciotto Canudo",
                        "cinema_hall_capacity": 750,
                        "tickets_available": 747
                    },
                    {
                        "...": "..."
                    },
                ]
            )
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Create a movie session",
    )
    def create(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Movie session detail view",
        examples=[
            OpenApiExample(
                "1",
                value={
                    "id": 1,
                    "show_time": "2024-10-08T13:00:00Z",
                    "movie": {
                        "id": 1,
                        "title": "The Departed",
                        "description": "An undercover cop and a mole in the"
                                       " police attempt to identify each other"
                                       " while infiltrating an Irishgang in"
                                       " South Boston.",
                        "duration": 151,
                        "genres": [
                            "Crime",
                            "Drama",
                            "Thriller"
                        ],
                        "actors": [
                            "Jack Nicholson",
                            "Leonardo DiCaprio",
                            "Matt Damon"
                        ],
                        "image": None
                    },
                    "cinema_hall": {
                        "id": 1,
                        "name": "Ricciotto Canudo",
                        "rows": 25,
                        "seats_in_row": 30,
                        "capacity": 750
                    },
                    "taken_places": [
                        {
                            "row": 1,
                            "seat": 1
                        },
                        {
                            "row": 2,
                            "seat": 3
                        },
                        {
                            "row": 2,
                            "seat": 4
                        }
                    ]
                }
            )
        ],
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Update a movie session",
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Partial update a movie session",
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Delete a movie session",
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class OrderPagination(PageNumberPagination):
    page_size = 1
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

    @extend_schema(
        summary="Get a paginated order list",
        examples=[
            OpenApiExample(
                name="Response body",
                response_only=True,
                value=[
                    {
                        "id": 1,
                        "tickets": [
                            {
                                "id": 1,
                                "...": "..."
                            },
                            {
                                "id": 2,
                                "...": "..."
                            }
                        ]
                    },
                    {
                        "id": 2,
                        "tickets": "..."
                    }
                ]
            )
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Create an order",
        examples=[
            OpenApiExample(
                name="Request body",
                value={
                    "tickets": [
                        {
                            "row": 1,
                            "seat": 1,
                            "movie_session": 1
                        },
                        {
                            "row": 1,
                            "seat": 2,
                            "movie_session": 1
                        },
                        {
                            "row": 1,
                            "seat": 3,
                            "movie_session": 1
                        }
                    ]
                },
                request_only=True
            ),
            OpenApiExample(
                name="Response body",
                value={
                    "id": 1,
                    "tickets": [
                        {
                            "id": 1,
                            "row": 1,
                            "seat": 1,
                            "movie_session": 1
                        },
                        {
                            "id": 2,
                            "row": 1,
                            "seat": 2,
                            "movie_session": 1
                        },
                        {
                            "id": 3,
                            "row": 1,
                            "seat": 3,
                            "movie_session": 1
                        }
                    ],
                    "created_at": "2025-04-23T11:27:15.601Z"
                },
                response_only=True
            )
        ]
    )
    def create(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
