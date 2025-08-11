from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    extend_schema_view,
    extend_schema,
    OpenApiExample,
    OpenApiParameter,
)
from rest_framework import status

from cinema.serializers import (
    GenreSerializer,
    ActorSerializer,
    CinemaHallSerializer
)


genre_viewset_schema = extend_schema_view(
    list=extend_schema(
        description="Get a list of all genres",
        responses={
            status.HTTP_200_OK: GenreSerializer,
        },
        examples=[
            OpenApiExample(
                name="ListGenresResponse",
                description="An example response for listing all genres",
                value=[
                    {
                        "id": 1,
                        "name": "Action"
                    },
                    {
                        "id": 2,
                        "name": "Adventures"
                    },
                ],
                response_only=True,
            ),
        ],
    ),
    create=extend_schema(
        description="Add a new genre",
        request=GenreSerializer,
        responses={
            status.HTTP_201_CREATED: GenreSerializer,
            status.HTTP_400_BAD_REQUEST: "Bad Request"
        },
        examples=[
            OpenApiExample(
                name="CreateGenreRequest",
                description="An example request to create a genre",
                value={
                    "name": "Sci-Fi"
                },
                request_only=True
            ),
            OpenApiExample(
                name="CreateGenreResponse",
                description="An example response after creating a genre",
                value={
                    "id": 3,
                    "name": "Sci-Fi"
                },
                response_only=True,
            ),
        ],
    ),
)


actor_viewset_schema = extend_schema_view(
    list=extend_schema(
        description="Get a list of all actors",
        responses={
            status.HTTP_200_OK: ActorSerializer,
        },
        examples=[
            OpenApiExample(
                name="ListActorsResponse",
                description="An example response for all actors",
                value=[
                    {
                        "id": 1,
                        "first_name": "John",
                        "last_name": "Doe",
                        "full_name": "John Doe"
                    },
                    {
                        "id": 2,
                        "first_name": "Jane",
                        "last_name": "Doe",
                        "full_name": "Jane Doe"
                    },
                ],
                response_only=True,
            ),
        ],
    ),
    create=extend_schema(
        description="Add a new actor",
        request=GenreSerializer,
        responses={
            status.HTTP_201_CREATED: ActorSerializer,
            status.HTTP_400_BAD_REQUEST: "Bad Request"
        },
        examples=[
            OpenApiExample(
                name="CreateActorRequest",
                description="An example request to create an actor",
                value={
                    "first_name": "John",
                    "last_name": "Doe",
                },
                request_only=True
            ),
            OpenApiExample(
                name="CreateActorResponse",
                description="An example response after creating an actor",
                value={
                    "id": 3,
                    "first_name": "John",
                    "last_name": "Doe",
                    "full_name": "John Doe"
                },
                response_only=True,
            ),
        ],
    ),
)


cinema_hall_viewset_schema = extend_schema_view(
    list=extend_schema(
        description="Get a list of all cinema halls",
        responses={
            status.HTTP_200_OK: CinemaHallSerializer,
        },
        examples=[
            OpenApiExample(
                name="ListCinemaHallsResponse",
                description="An example response for all cinema halls",
                value=[
                    {
                        "id": 1,
                        "name": "CinemaHall 1",
                        "rows": 20,
                        "seats_in_row": 30,
                        "capacity": 600.
                    },
                    {
                        "id": 2,
                        "name": "CinemaHall 2",
                        "rows": 20,
                        "seats_in_row": 20,
                        "capacity": 400.
                    }
                ]
            )
        ]

    ),
    create=extend_schema(
        description="Add a new cinema hall",
        request=CinemaHallSerializer,
        responses={
            status.HTTP_201_CREATED: CinemaHallSerializer,
            status.HTTP_400_BAD_REQUEST: "Bad Request"
        },
        examples=[
            OpenApiExample(
                name="CreateCinemaHallRequest",
                description="An example request to create a cinema hall",
                value={
                    "name": "CinemaHall 3",
                    "rows": 20,
                    "seats_in_row": 20
                },
                request_only=True
            ),
            OpenApiExample(
                name="CreateCinemaHallResponse",
                description="An example response after creating a cinema hall",
                value={
                    "id": 3,
                    "name": "CinemaHall 3",
                    "rows": 20,
                    "seats_in_row": 20,
                    "capacity": 400
                },
                response_only=True,
            ),
        ],
    ),
)


movie_session_viewset_schema = extend_schema_view(
    list=extend_schema(
        description="Get a list of all movie sessions",
        parameters=[
            OpenApiParameter(
                name="date",
                description="Filter movie session "
                            "by date in format YYYY-MM-DD",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                required=False,
            ),
            OpenApiParameter(
                name="movie_id",
                description="Filter movie session by movie ids",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
            )
        ]
    ),
    create=extend_schema(
        description="Add a new movie session",
    ),
    retrieve=extend_schema(
        description="Get movie session details",
    ),
    update=extend_schema(
        description="Update movie session details",
    ),
    partial_update=extend_schema(
        description="Partially update movie session details",
    ),
    destroy=extend_schema(
        description="Delete movie session",
    ),
)


movie_viewset_schema = extend_schema_view(
    list=extend_schema(
        description="Get a list of all movies",
        parameters=[
            OpenApiParameter(
                name="title",
                description="Filter movie by title, case-insensitive."
                            "Multiple values can be provided",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
            ),
            OpenApiParameter(
                name="genres",
                description="Filter movie by genre ids."
                            "Multiple values can be provided",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
            ),
            OpenApiParameter(
                name="actors",
                description="Filter movie by actor ids."
                            "Multiple values can be provided",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False
            )
        ]
    ),
    create=extend_schema(
        description="Add a new movie",
    ),
    retrieve=extend_schema(
        description="Get movie details",
    ),
    upload_image=extend_schema(
        description="Upload an image for a specific movie.",
    )
)


order_viewset_schema = extend_schema_view(
    list=extend_schema(
        description="Get a list of all orders.",
    ),
    create=extend_schema(
        description="Add a new order.",
    ),
)
