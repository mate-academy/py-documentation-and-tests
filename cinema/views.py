from datetime import datetime

from django.db.models import F, Count
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiResponse,
    OpenApiExample,
    OpenApiParameter
)
from rest_framework import viewsets, mixins, status
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
from cinema_service.utils.schema_responses import (
    SCHEMA_API_RESPONSE_401,
    SCHEMA_API_RESPONSE_429,
    SCHEMA_API_RESPONSE_403
)


@extend_schema_view(
    list=extend_schema(
        summary="Genres list",
        description="""
        Returns genres list.
        Request is allowed only for authenticated users.
        Otherwise, returns 401 status code.
        """,
        request=None,
        methods=["GET"],
        tags=["genres"],
        examples=[
            OpenApiExample(
                value={
                    "id": 1,
                    "name": "Action"
                },
                name="Action genre",
                response_only=True,
            )
        ],
        responses={
            200: OpenApiResponse(
                response=GenreSerializer,
                description="Returns list of genres.",
            ),
            401: SCHEMA_API_RESPONSE_401,
            429: SCHEMA_API_RESPONSE_429,
        }
    ),
    create=extend_schema(
        summary="Genre create",
        description="""
        Returns created genre.
        Request is allowed only for admin users.
        Otherwise, returns 403 status code.
        """,
        request=None,
        methods=["POST"],
        tags=["genres"],
        examples=[
            OpenApiExample(
                value={
                    "id": 1,
                    "name": "Action"
                },
                name="Created action genre",
                response_only=True,
            ),
            OpenApiExample(
                value={
                    "name": "Action"
                },
                name="Action genre",
                request_only=True,
            )
        ],
        responses={
            201: OpenApiResponse(
                response=GenreSerializer,
                description="Returns created genre.",
            ),
            403: SCHEMA_API_RESPONSE_403,
            429: SCHEMA_API_RESPONSE_429,
        }
    ),
)
class GenreViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)


@extend_schema_view(
    create=extend_schema(
        summary="Actor create",
        tags=["actors"],
        methods=["POST"],
        request=ActorSerializer,
        examples=[
            OpenApiExample(
                value={
                    "first_name": "Harry",
                    "last_name": "Potter",
                },
                name="Harry Potter",
                request_only=True,
            ),
            OpenApiExample(
                value={
                    "id": 1,
                    "first_name": "Harry",
                    "last_name": "Potter",
                    "full_name": "Harry Potter",
                },
                name="Harry Potter",
                response_only=True,
            )
        ],
        description="""
        Actor creation view.
        Returns details of created actor.
        Request is allowed only for admin users.
        Otherwise, returns 403 status code.
        """,
        responses={
            201: OpenApiResponse(
                response=ActorSerializer,
                description="Returns created actor.",
            ),
            401: SCHEMA_API_RESPONSE_401,
            403: SCHEMA_API_RESPONSE_403,
            429: SCHEMA_API_RESPONSE_429,
        }
    )
)
class ActorViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    queryset = Actor.objects.all()
    serializer_class = ActorSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    @extend_schema(
        methods=["GET"],
        tags=["actors"],
        summary="Actors list",
        description="""
        Returns all existing actors list.
        Request is allowed only for authenticated users.
        Otherwise, returns 401 status code.
        """,
        request=None,
        responses={
            200: OpenApiResponse(
                response=ActorSerializer,
                description="List of actors",
                examples=[
                    OpenApiExample(
                        value={
                            "id": 1,
                            "first_name": "Harry",
                            "last_name": "Potter",
                            "full_name": "Harry Potter",
                        },
                        name="List of actors",
                        response_only=True,
                    )
                ]
            ),
            401: SCHEMA_API_RESPONSE_401,
            429: SCHEMA_API_RESPONSE_429,
        },
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


@extend_schema_view(
    list=extend_schema(
        summary="Cinema hall list",
        methods=["GET"],
        tags=["cinema_hall"],
        description="""
        Returns all existing cinema halls list.
        Request is allowed only for authenticated users.
        Otherwise, returns 401 status code.
        """,
        examples=[
            OpenApiExample(
                value={
                    "id": 5,
                    "name": "Ricciotto Canudo",
                    "rows": 7,
                    "seats_in_row": 19,
                    "capacity": 133,
                },
                response_only=True,
                name="Ricciotto Canudo cinema hall.",
            )
        ],
        responses={
            200: OpenApiResponse(
                response=CinemaHallSerializer,
                description="Returns list of cinema halls",
            ),
            401: SCHEMA_API_RESPONSE_401,
            429: SCHEMA_API_RESPONSE_429,
        }
    ),
    create=extend_schema(
        summary="Cinema hall create",
        description="""
        Returns all existing cinema halls list.
        Request is allowed only for admin users.
        Otherwise, returns 403 status code.
        """,
        methods=["POST"],
        tags=["cinema_hall"],
        request=CinemaHallSerializer,
        examples=[
            OpenApiExample(
                value={
                    "name": "Ricciotto Canudo",
                    "rows": 7,
                    "seats_in_row": 19,
                },
                request_only=True,
                name="Ricciotto Canudo cinema hall.",
            ),
            OpenApiExample(
                value={
                    "id": 5,
                    "name": "Ricciotto Canudo",
                    "rows": 7,
                    "seats_in_row": 19,
                    "capacity": 133,
                },
                response_only=True,
                name="Ricciotto Canudo cinema hall.",
            )
        ],
        responses={
            201: OpenApiResponse(
                response=CinemaHallSerializer,
                description="Returns created cinema hall.",
            ),
            401: SCHEMA_API_RESPONSE_401,
            403: SCHEMA_API_RESPONSE_403,
            429: SCHEMA_API_RESPONSE_429,
        }
    )
)
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
        summary="Movies list",
        description="""
        Returns all existing movies list, filtered by query params.
        Request is allowed only for authenticated users.
        Otherwise, returns 401 status code.
        """,
        methods=["GET"],
        tags=["movies"],
        examples=[
            OpenApiExample(
                value={
                    "id": 1,
                    "title": "Inception",
                    "description": """
                    A thief who steals corporate secrets
                    through the use of dream-sharing technology
                    is given the inverse task of planting an idea
                    into the mind of a C.E.O.
                    """,
                    "duration": 148,
                    "genres": [
                        "Action",
                        "Adventure",
                        "Sci-Fi"
                    ],
                    "actors": [
                        "Leonardo DiCaprio",
                        "Joseph Gordon-Levitt",
                        "Elliot Page"
                    ],
                    "image": None
                },
                name="List of movies",
                response_only=True,
            )
        ],
        parameters=[
            OpenApiParameter(
                name="title",
                required=False,
                type=OpenApiTypes.STR,
                description="Filter movies by title.",
                examples=[
                    OpenApiExample(
                        value="",
                        name="None",
                        request_only=True,
                    ),
                    OpenApiExample(
                        value="Inception",
                        name="Inception",
                        request_only=True,
                    ),
                    OpenApiExample(
                        value="The Departed",
                        name="The Departed",
                        request_only=True,
                    ),
                ]
            ),
            OpenApiParameter(
                name="genres",
                type={"type": "array", "items": {"type": "number"}},
                required=False,
                description="Filter movies by genres.",
                examples=[
                    OpenApiExample(
                        value="",
                        name="None",
                        request_only=True,
                    ),
                    OpenApiExample(
                        value=[1],
                        name="Crime",
                        request_only=True
                    ),
                    OpenApiExample(
                        value=[1, 3],
                        name="Crime, Thriller",
                        request_only=True,
                    ),
                ]
            ),
            OpenApiParameter(
                name="actors",
                type={"type": "array", "items": {"type": "number"}},
                required=False,
                description="Filter movies by actors.",
                examples=[
                    OpenApiExample(
                        value="",
                        name="None",
                        request_only=True,
                    ),
                    OpenApiExample(
                        value=[1],
                        name="Jack Nicholson",
                        request_only=True,
                    ),
                    OpenApiExample(
                        value=[1, 1],
                        name="Jack Nicholson, Leonardo DiCaprio",
                        request_only=True,
                    ),
                ]
            )
        ],
        responses={
            200: OpenApiResponse(
                response=MovieListSerializer,
                description="Returns list of movies",
            ),
            401: SCHEMA_API_RESPONSE_401,
            429: SCHEMA_API_RESPONSE_429,
        }

    ),
    retrieve=extend_schema(
        summary="Movie details",
        request=None,
        methods=["GET"],
        tags=["movies"],
        description="""
        Returns a movie details.
        Request is allowed only for authenticated users.
        Otherwise, returns 401 status code.
        """,
        examples=[
            OpenApiExample(
                value={
                    "id": 1,
                    "title": "Inception",
                    "description": """
                    A thief who steals corporate secrets through the use
                    of dream-sharing technology is given the inverse task
                    of planting an idea into the mind of a C.E.O.
                    """,
                    "duration": 148,
                    "genres": [
                        "Action",
                        "Adventure",
                        "Sci-Fi"
                    ],
                    "actors": [
                        "Leonardo DiCaprio",
                        "Joseph Gordon-Levitt",
                        "Elliot Page"
                    ],
                    "image": None
                },
                name="Inception movie detail",
                response_only=True,
            )
        ],
        responses={
            200: OpenApiResponse(
                response=MovieDetailSerializer,
                description="Returns movie details.",
            ),
            401: SCHEMA_API_RESPONSE_401,
            429: SCHEMA_API_RESPONSE_429,
        }
    )
)
class MovieViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Movie.objects.prefetch_related("genres", "actors")
    serializer_class = MovieSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    @extend_schema(
        summary="Movie create",
        description="""
        Returns created movie.
        Request is allowed only for admin users.
        Otherwise, returns 403 status code.
        """,
        methods=["POST"],
        tags=["movies"],
        request=MovieSerializer,
        examples=[
            OpenApiExample(
                value={
                    "title": "Inception",
                    "description": """
                    A thief who steals corporate secrets through the use of
                    dream-sharing technology is given the
                    inverse task of planting an idea into the
                    mind of a C.E.O.
                    """,
                    "duration": 148,
                    "genres": [1, 2, 3],
                    "actors": [1, 2, 3],
                },
                name="Create Inception movie",
                request_only=True,
            ),
            OpenApiExample(
                value={
                    "id": 1,
                    "title": "Inception",
                    "description": """
                    A thief who steals corporate secrets through the use of
                    dream-sharing technology is given the inverse task of
                    planting an idea into the mind of a C.E.O.
                    """,
                    "duration": 148,
                    "genres": [
                        "Action",
                        "Adventure",
                        "Sci-Fi"
                    ],
                    "actors": [
                        "Leonardo DiCaprio",
                        "Joseph Gordon-Levitt",
                        "Elliot Page"
                    ],
                    "image": None
                },
                name="Created Inception movie detail",
                response_only=True,
            )
        ],
        responses={
            201: OpenApiResponse(
                response=MovieDetailSerializer,
                description="Returns created movie.",
            ),
            401: SCHEMA_API_RESPONSE_401,
            403: SCHEMA_API_RESPONSE_403,
            429: SCHEMA_API_RESPONSE_429,
        }
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

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
        summary="Create image for movie",
        description="""
        Returns created image for movie.
        Request is allowed only for admin users.
        Otherwise, returns 403 status code.
        """,
        tags=["movies"],
        methods=["POST"],
        examples=[
            OpenApiExample(
                value={
                    "image": "https://your-uploaded-file.jpg"
                },
                name="Create image for movie",
                request_only=True,
            ),
            OpenApiExample(
                value={
                    "id": 1,
                    "image": """
                    http://127.0.0.1:8000/media/uploads/movies/your-uploaded-file.jpg
                    """
                },
                name="Created image for movie",
                response_only=True,
            )
        ],
        request=MovieImageSerializer,
        responses={
            200: OpenApiResponse(
                response=MovieImageSerializer,
                description="Returns created image for movie.",
            ),
            401: SCHEMA_API_RESPONSE_401,
            403: SCHEMA_API_RESPONSE_403,
            404: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                examples=[
                    OpenApiExample(
                        value={
                            "detail": "Bad request."
                        },
                        name="Bad request.",
                        response_only=True,
                    ),
                ],
                description="Bad request."
            ),
            429: SCHEMA_API_RESPONSE_429,
        }
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
        summary="Movie session list",
        tags=["movie_session"],
        methods=["GET"],
        request=None,
        description="""
        Returns movie session list.
        Request is allowed only for authenticated users.
        Otherwise, returns 401 status code.
        """,
        parameters=[
            OpenApiParameter(
                type=OpenApiTypes.DATE,
                name="date",
                required=False,
                description="Filter movie sessions by date.",
                examples=[
                    OpenApiExample(
                        value="",
                        name="None",
                        request_only=True,
                    ),
                    OpenApiExample(
                        value="2024-10-08",
                        name="2024-10-08",
                        request_only=True,
                    ),
                    OpenApiExample(
                        value="2024-10-09",
                        name="2024-10-09",
                        request_only=True,
                    ),
                ]
            ),
            OpenApiParameter(
                type=OpenApiTypes.INT,
                name="movie",
                required=False,
                description="Filter movie sessions by movie id.",
                examples=[
                    OpenApiExample(
                        value="",
                        name="None",
                        request_only=True,
                    ),
                    OpenApiExample(
                        value=1,
                        name="The Departed movie id",
                        request_only=True,
                    ),
                    OpenApiExample(
                        value=2,
                        name="Inception movie id",
                        request_only=True,
                    )
                ]
            )
        ],
        examples=[
            OpenApiExample(
                value={
                    "id": 1,
                    "show_time": "2024-10-08T13:00:00",
                    "movie_title": "The Departed",
                    "movie_image": None,
                    "cinema_hall_name": "Ricciotto Canudo",
                    "cinema_hall_capacity": 750,
                    "tickets_available": 747
                },
                response_only=True,
                name="List of movie sessions",
            )
        ],
        responses={
            200: OpenApiResponse(
                response=MovieSessionListSerializer,
                description="Returns movie session list.",
            ),
            401: SCHEMA_API_RESPONSE_401,
            429: SCHEMA_API_RESPONSE_429,
        }
    ),
    retrieve=extend_schema(
        summary="Movie session detail",
        description="""
        Returns movie session details.
        Request is allowed only for authenticated users.
        Otherwise, returns 401 status code.
        """,
        tags=["movie_session"],
        methods=["GET"],
        request=None,
        examples=[
            OpenApiExample(
                value={
                    "id": 1,
                    "show_time": "2024-10-08T13:00:00",
                    "movie": {
                        "id": 1,
                        "title": "The Departed",
                        "description": """
                        An undercover cop and a mole in the police attempt to
                        identify each other while infiltrating an
                        Irishgang in South Boston.
                        """,
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
                },
                name="Movie session detail",
                response_only=True,
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=MovieSessionDetailSerializer,
                description="Returns movie session details.",
            ),
            401: SCHEMA_API_RESPONSE_401,
            429: SCHEMA_API_RESPONSE_429,
        }
    ),
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
        summary="Order list",
        description="""
        Returns paginated orders list for authenticated user.
        Request is allowed only for authenticated users.
        Otherwise, returns 401 status code.
        """,
        request=None,
        methods=["GET"],
        tags=["orders"],
        examples=[
            OpenApiExample(
                value={
                    "id": 1,
                    "tickets": [
                        {
                            "id": 1,
                            "row": 1,
                            "seat": 1,
                            "movie_session": {
                                "id": 1,
                                "show_time": "2024-10-08T13:00:00",
                                "movie_title": "The Departed",
                                "movie_image": None,
                                "cinema_hall_name": "Ricciotto Canudo",
                                "cinema_hall_capacity": 750
                            }
                        },
                    ],
                    "created_at": "2022-08-09T09:06:18.876000"
                },
                name="Paginated list of orders",
                response_only=True,
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=OrderListSerializer,
                description="Returns paginated list of orders.",
            ),
            401: SCHEMA_API_RESPONSE_401,
            429: SCHEMA_API_RESPONSE_429,
        }
    ),
    create=extend_schema(
        summary="Order create",
        tags=["orders"],
        methods=["POST"],
        description="""
        Returns created order.
        row, seat and movie_session should be unique.
        Request is allowed only for admin users.
        Otherwise, returns 403 status code.
        """,
        examples=[
            OpenApiExample(
                value={
                    "tickets": []
                },
                name="Create order without tickets",
                request_only=True,
            ),
            OpenApiExample(
                value={
                    "tickets": [
                        {
                            "row": 1,
                            "seat": 4,
                            "movie_session": 2
                        }
                    ]
                },
                name="Create order with tickets",
                request_only=True,
            ),
            OpenApiExample(
                value={
                    "id": 1,
                    "tickets": [
                        {
                            "id": 1,
                            "row": 1,
                            "seat": 4,
                            "movie_session": 2
                        }
                    ],
                    "created_at": "2025-10-25T14:05:23.418131"
                },
                name="Created order with tickets",
                response_only=True,
            ),
            OpenApiExample(
                value={
                    "id": 2,
                    "tickets": [],
                    "created_at": "2025-10-25T14:05:23.418131"
                },
                name="Created order without tickets",
                response_only=True,
            )
        ],
        responses={
            201: OpenApiResponse(
                response=OrderSerializer,
                description="Returns created order.",
            ),
            401: SCHEMA_API_RESPONSE_401,
            403: SCHEMA_API_RESPONSE_403,
            400: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                examples=[
                    OpenApiExample(
                        value={
                            "tickets": [
                                {
                                    "non_field_errors": [
                                        """
                                        The fields movie_session, row,
                                        seat must make a unique set.
                                        """
                                    ]
                                }
                            ]
                        },
                        name="Tickets data validation error.",
                        response_only=True,
                    ),
                    OpenApiExample(
                        value={
                            "detail": "Bad request."
                        },
                        name="Bad request.",
                        response_only=True,
                    ),
                ],
            ),
            429: SCHEMA_API_RESPONSE_429,
        }
    )
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
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == "list":
            return OrderListSerializer

        return OrderSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
