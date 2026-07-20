from datetime import datetime

from django.db.models import F, Count
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    extend_schema_view,
    OpenApiResponse
)
from rest_framework import viewsets, mixins, status
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


BAD_REQUEST_RESPONSE = OpenApiResponse(
    description=(
        "The request data is invalid. "
        "The response contains validation errors for the submitted fields."
    ),
)

UNAUTHORIZED_RESPONSE = OpenApiResponse(
    description=(
        "Authentication credentials were not provided, the access token "
        "is invalid, or the access token has expired."
    ),
)

FORBIDDEN_RESPONSE = OpenApiResponse(
    description=(
        "The user is authenticated but does not have administrator "
        "permissions required to perform this operation."
    ),
)

NOT_FOUND_RESPONSE = OpenApiResponse(
    description="The requested object was not found.",
)

NO_CONTENT_RESPONSE = OpenApiResponse(
    description=(
        "The object was deleted successfully. "
        "The response does not contain a body."
    ),
)

TOO_MANY_REQUESTS_RESPONSE = OpenApiResponse(
    description=(
        "The request was rejected because the allowed request rate "
        "was exceeded. Authenticated users are limited to 30 requests "
        "per minute. The response may include a Retry-After header."
    ),
)


@extend_schema_view(
    list=extend_schema(
        summary="List genres",
        description=(
            "Return a list of all movie genres stored in the system. "
            "No filtering parameters are currently supported. "
            "A valid JWT access token is required. Any authenticated user "
            "can perform this operation."
        ),
        responses={
            200: OpenApiResponse(
                description=(
                    "The list of genres was returned successfully. "
                    "If no genres exist, an empty list is returned."
                ),
            ),
            401: UNAUTHORIZED_RESPONSE,
            429: TOO_MANY_REQUESTS_RESPONSE,
        },
        tags=["Genres"],
    ),
    create=extend_schema(
        summary="Create genre",
        description=(
            "Create a new movie genre using the data provided in the "
            "request body. The submitted data must satisfy all serializer "
            "and model validation rules. A valid JWT access"
            " token is required. Only users with administrator"
            " permissions can perform "
            "this operation."
        ),
        responses={
            201: OpenApiResponse(
                description=(
                    "The genre was created successfully. "
                    "The response contains the created genre."
                ),
            ),
            400: BAD_REQUEST_RESPONSE,
            401: UNAUTHORIZED_RESPONSE,
            403: FORBIDDEN_RESPONSE,
            429: TOO_MANY_REQUESTS_RESPONSE,
        },
        tags=["Genres"],
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
    list=extend_schema(
        summary="List actors",
        description=(
            "Return a list of all actors stored in the system. "
            "No filtering parameters are currently supported. "
            "A valid JWT access token is required. Any authenticated user "
            "can perform this operation."
        ),
        responses={
            200: OpenApiResponse(
                description=(
                    "The list of actors was returned successfully. "
                    "If no actors exist, an empty list is returned."
                ),
            ),
            401: UNAUTHORIZED_RESPONSE,
            429: TOO_MANY_REQUESTS_RESPONSE,
        },
        tags=["Actors"],
    ),
    create=extend_schema(
        summary="Create actor",
        description=(
            "Create a new actor using the data provided in the request body. "
            "The submitted data must satisfy all serializer and model "
            "validation rules. A valid JWT access token is required. "
            "Only users with administrator permissions can perform "
            "this operation."
        ),
        responses={
            201: OpenApiResponse(
                description=(
                    "The actor was created successfully. "
                    "The response contains the created actor."
                ),
            ),
            400: BAD_REQUEST_RESPONSE,
            401: UNAUTHORIZED_RESPONSE,
            403: FORBIDDEN_RESPONSE,
            429: TOO_MANY_REQUESTS_RESPONSE,
        },
        tags=["Actors"],
    ),
)
class ActorViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    GenericViewSet,
):
    queryset = Actor.objects.all()
    serializer_class = ActorSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)


@extend_schema_view(
    list=extend_schema(
        summary="List cinema halls",
        description=(
            "Return a list of all cinema halls stored in the system. "
            "Each item contains the hall information provided by the cinema "
            "hall serializer, including its seating dimensions. "
            "No filtering parameters are currently supported. "
            "A valid JWT access token is required. Any authenticated user "
            "can perform this operation."
        ),
        responses={
            200: OpenApiResponse(
                description=(
                    "The list of cinema halls was returned successfully. "
                    "If no cinema halls exist, an empty list is returned."
                ),
            ),
            401: UNAUTHORIZED_RESPONSE,
            429: TOO_MANY_REQUESTS_RESPONSE,
        },
        tags=["Cinema Halls"],
    ),
    create=extend_schema(
        summary="Create cinema hall",
        description=(
            "Create a new cinema hall using the data provided in the request "
            "body. The hall name, number of rows and number of seats in each "
            "row must satisfy all serializer and model validation rules. "
            "A valid JWT access token is required. Only users with "
            "administrator permissions can perform this operation."
        ),
        responses={
            201: OpenApiResponse(
                description=(
                    "The cinema hall was created successfully. "
                    "The response contains the created cinema hall."
                ),
            ),
            400: BAD_REQUEST_RESPONSE,
            401: UNAUTHORIZED_RESPONSE,
            403: FORBIDDEN_RESPONSE,
            429: TOO_MANY_REQUESTS_RESPONSE,
        },
        tags=["Cinema Halls"],
    ),
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
    create=extend_schema(
        summary="Create movie",
        description=(
            "Create a new movie using the data provided in the request body. "
            "Referenced genres and actors must exist and the submitted data "
            "must satisfy all serializer validation rules. The movie poster "
            "is not uploaded through this endpoint; use the separate "
            "upload-image endpoint to upload or replace it. "
            "A valid JWT access token is required. Only users with "
            "administrator permissions can perform this operation."
        ),
        responses={
            201: OpenApiResponse(
                description=(
                    "The movie was created successfully. "
                    "The response contains the created movie."
                ),
            ),
            400: OpenApiResponse(
                description=(
                    "The submitted movie data is invalid. This may occur "
                    "when a required field is missing, a field has an invalid "
                    "value, or a referenced genre or actor is invalid."
                ),
            ),
            401: UNAUTHORIZED_RESPONSE,
            403: FORBIDDEN_RESPONSE,
            429: TOO_MANY_REQUESTS_RESPONSE,
        },
        tags=["Movies"],
    ),
    retrieve=extend_schema(
        summary="Retrieve movie",
        description=(
            "Return detailed information about the "
            "movie identified by its ID. "
            "The response is generated using the "
            "movie detail serializer and "
            "includes the related genres and actors. "
            "A valid JWT access token is required. "
            "Any authenticated user "
            "can perform this operation."
        ),
        responses={
            200: OpenApiResponse(
                description=(
                    "The movie was found and its detailed information "
                    "was returned successfully."
                ),
            ),
            401: UNAUTHORIZED_RESPONSE,
            404: OpenApiResponse(
                description="A movie with the specified ID was not found.",
            ),
            429: TOO_MANY_REQUESTS_RESPONSE,
        },
        tags=["Movies"],
    ),
    upload_image=extend_schema(
        summary="Upload movie image",
        description=(
            "Upload an image for the movie identified by its ID. "
            "The submitted file is validated by MovieImageSerializer. "
            "If the movie already has an image, its image field is updated "
            "with the newly submitted file. The request should use "
            "multipart/form-data. A valid JWT access token is required. "
            "Only users with administrator permissions can perform "
            "this operation."
        ),
        request=MovieImageSerializer,
        responses={
            200: OpenApiResponse(
                description=(
                    "The image was uploaded successfully. "
                    "The response contains the serialized "
                    "movie image data."
                ),
            ),
            400: OpenApiResponse(
                description=(
                    "The submitted image data is "
                    "invalid. This may occur "
                    "when the image is missing, the file"
                    " is not a valid image, "
                    "or the file does not satisfy "
                    "serializer validation rules."
                ),
            ),
            401: UNAUTHORIZED_RESPONSE,
            403: FORBIDDEN_RESPONSE,
            404: OpenApiResponse(
                description="A movie with the specified ID was not found.",
            ),
            429: TOO_MANY_REQUESTS_RESPONSE,
        },
        tags=["Movies"],
    ),
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
        summary="List movies",
        description=(
                "Return a list of movies stored "
                "in the system. The result can be "
                "filtered by a case-insensitive "
                "partial title match, genre IDs and "
                "actor IDs. Multiple filters can "
                "be applied in the same request. "
                "When several genre or actor IDs "
                "are supplied, a movie matches the "
                "corresponding filter when it is "
                "related to at least one of those IDs. "
                "When both genre and actor filters"
                " are supplied, the movie must satisfy "
                "both groups of conditions. "
                "Duplicate results produced by "
                "many-to-many relationships are "
                "removed. A valid JWT access token "
                "is required. Any authenticated "
                "user can perform this operation."
        ),
        parameters=[
            OpenApiParameter(
                name="title",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Text that must occur anywhere "
                    "in the movie title. "
                    "The comparison is case-insensitive."
                ),
            ),
            OpenApiParameter(
                name="genres",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Comma-separated genre IDs. "
                    "A movie is returned when it "
                    "belongs to at least one of "
                    "the specified genres."
                ),
            ),
            OpenApiParameter(
                name="actors",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Comma-separated actor IDs. "
                    "A movie is returned when at least "
                    "one of the specified actors "
                    "is associated with the movie."
                ),
            ),
        ],
        responses={
            200: OpenApiResponse(
                description=(
                    "The movie list was returned successfully. "
                    "If no movies satisfy the "
                    "supplied filters, an empty list "
                    "is returned."
                ),
            ),
            401: UNAUTHORIZED_RESPONSE,
            429: TOO_MANY_REQUESTS_RESPONSE,
        },
        tags=["Movies"],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

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
    create=extend_schema(
        summary="Create movie session",
        description=(
            "Create a new movie session using the data provided in the "
            "request body. The referenced movie and cinema hall must exist, "
            "and the show time and other fields must satisfy all serializer "
            "validation rules. A valid JWT access token is required. "
            "Only users with administrator permissions can perform "
            "this operation."
        ),
        responses={
            201: OpenApiResponse(
                description=(
                    "The movie session was created successfully. "
                    "The response contains the created movie session."
                ),
            ),
            400: OpenApiResponse(
                description=(
                    "The submitted movie session data is invalid. "
                    "This may occur when a required field is missing, a field "
                    "has an invalid value, or a related object is invalid."
                ),
            ),
            401: UNAUTHORIZED_RESPONSE,
            403: FORBIDDEN_RESPONSE,
            429: TOO_MANY_REQUESTS_RESPONSE,
        },
        tags=["Movie Sessions"],
    ),
    retrieve=extend_schema(
        summary="Retrieve movie session",
        description=(
            "Return detailed information about "
            "the movie session identified "
            "by its ID. The response is generated"
            " using the movie session "
            "detail serializer and includes "
            "information about the related "
            "movie and cinema hall. The queryset"
            " also calculates the number "
            "of available tickets by subtracting"
            " the number of created tickets "
            "from the total number of seats "
            "in the cinema hall. "
            "A valid JWT access token is "
            "required. Any authenticated user "
            "can perform this operation."
        ),
        responses={
            200: OpenApiResponse(
                description=(
                    "The movie session was found and its detailed information "
                    "was returned successfully."
                ),
            ),
            401: UNAUTHORIZED_RESPONSE,
            404: OpenApiResponse(
                description=(
                    "A movie session with the specified ID was not found."
                ),
            ),
            429: TOO_MANY_REQUESTS_RESPONSE,
        },
        tags=["Movie Sessions"],
    ),
    update=extend_schema(
        summary="Update movie session",
        description=(
            "Completely update the movie session identified by its ID. "
            "Because this operation uses PUT, the request should contain "
            "values for all required writable fields. Fields are validated "
            "using the movie session serializer. A valid JWT access token "
            "is required. Only users with administrator permissions can "
            "perform this operation."
        ),
        responses={
            200: OpenApiResponse(
                description=(
                    "The movie session was updated successfully. "
                    "The response contains the updated movie session."
                ),
            ),
            400: BAD_REQUEST_RESPONSE,
            401: UNAUTHORIZED_RESPONSE,
            403: FORBIDDEN_RESPONSE,
            404: OpenApiResponse(
                description=(
                    "A movie session with the specified ID was not found."
                ),
            ),
            429: TOO_MANY_REQUESTS_RESPONSE,
        },
        tags=["Movie Sessions"],
    ),
    partial_update=extend_schema(
        summary="Partially update movie session",
        description=(
            "Update one or more fields of the movie session identified by "
            "its ID. Because this operation uses PATCH, fields omitted from "
            "the request remain unchanged. The submitted fields are validated "
            "using the movie session serializer. A valid JWT access token "
            "is required. Only users with administrator permissions can "
            "perform this operation."
        ),
        responses={
            200: OpenApiResponse(
                description=(
                    "The submitted movie session fields were updated "
                    "successfully. The response contains the updated "
                    "movie session."
                ),
            ),
            400: BAD_REQUEST_RESPONSE,
            401: UNAUTHORIZED_RESPONSE,
            403: FORBIDDEN_RESPONSE,
            404: OpenApiResponse(
                description=(
                    "A movie session with the specified ID was not found."
                ),
            ),
            429: TOO_MANY_REQUESTS_RESPONSE,
        },
        tags=["Movie Sessions"],
    ),
    destroy=extend_schema(
        summary="Delete movie session",
        description=(
            "Permanently delete the movie session identified by its ID. "
            "A valid JWT access token is required. Only users with "
            "administrator permissions can perform this operation. "
            "A successful response does not contain a response body."
        ),
        responses={
            204: NO_CONTENT_RESPONSE,
            401: UNAUTHORIZED_RESPONSE,
            403: FORBIDDEN_RESPONSE,
            404: OpenApiResponse(
                description=(
                    "A movie session with the "
                    "specified ID was not found."
                ),
            ),
            429: TOO_MANY_REQUESTS_RESPONSE,
        },
        tags=["Movie Sessions"],
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

    @extend_schema(
        summary="List movie sessions",
        description=(
                "Return a list of movie sessions"
                " stored in the system. "
                "The result can be filtered by "
                "an exact show date and by movie ID. "
                "Both filters can be applied in "
                "the same request, in which case only "
                "sessions satisfying both conditions"
                " are returned. Each session "
                "queryset item is annotated with "
                "the number of available tickets, "
                "calculated as the total number of "
                "seats in the cinema hall minus "
                "the number of tickets created "
                "for that session. "
                "A valid JWT access token is required."
                " Any authenticated user "
                "can perform this operation."
        ),
        parameters=[
            OpenApiParameter(
                name="date",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Exact calendar date of the "
                    "movie session show time. "
                    "The value must use the "
                    "YYYY-MM-DD format."
                ),
            ),
            OpenApiParameter(
                name="movie",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "ID of the movie. Only sessions "
                    "associated with this movie "
                    "are returned."
                ),
            ),
        ],
        responses={
            200: OpenApiResponse(
                description=(
                    "The movie session list was "
                    "returned successfully. "
                    "If no sessions satisfy the "
                    "supplied filters, an empty list "
                    "is returned."
                ),
            ),
            401: UNAUTHORIZED_RESPONSE,
            429: TOO_MANY_REQUESTS_RESPONSE,
        },
        tags=["Movie Sessions"],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

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
        summary="List current user's orders",
        description=(
            "Return a paginated list of orders belonging to the currently "
            "authenticated user. Orders belonging to other users are excluded "
            "by the queryset and cannot be retrieved through this endpoint. "
            "Each page contains up to 10 orders. The response representation "
            "may include related tickets and information about their movie "
            "sessions, movies and cinema halls. A valid JWT access token "
            "is required."
        ),
        parameters=[
            OpenApiParameter(
                name="page",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=False,
                description=(
                    "Number of the results page to return. "
                    "Page numbering starts from 1."
                ),
            ),
        ],
        responses={
            200: OpenApiResponse(
                description=(
                    "The requested page of the current user's orders was "
                    "returned successfully. If the user has no orders, "
                    "the results collection is empty."
                ),
            ),
            401: UNAUTHORIZED_RESPONSE,
            404: OpenApiResponse(
                description=(
                    "The requested page number does not exist in the "
                    "paginated result set."
                ),
            ),
            429: TOO_MANY_REQUESTS_RESPONSE,
        },
        tags=["Orders"],
    ),
    create=extend_schema(
        summary="Create order",
        description=(
            "Create a new order for the currently authenticated user. "
            "The user is assigned automatically from request.user and does "
            "not need to be supplied in the request body. The submitted order "
            "and ticket data are validated by the order serializer. "
            "A valid JWT access token is required. Administrator permissions "
            "are not required."
        ),
        responses={
            201: OpenApiResponse(
                description=(
                    "The order and its related tickets were created "
                    "successfully. The response contains the created order."
                ),
            ),
            400: OpenApiResponse(
                description=(
                    "The submitted order or ticket data is invalid. "
                    "The response contains validation errors explaining "
                    "which values were rejected."
                ),
            ),
            401: UNAUTHORIZED_RESPONSE,
            429: TOO_MANY_REQUESTS_RESPONSE,
        },
        tags=["Orders"],
    ),
)
class OrderViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    GenericViewSet,
):
    queryset = Order.objects.prefetch_related(
        "tickets__movie_session__movie",
        "tickets__movie_session__cinema_hall"
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
