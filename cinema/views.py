from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from rest_framework import viewsets
from .models import Movie, MovieSession
from .serializers import MovieSerializer, MovieSessionSerializer

# ... other imports

@extend_schema(
    parameters=[
        OpenApiParameter(
            "genres",
            type=OpenApiTypes.STR,
            description="Filter by genre IDs (comma separated). Ex: ?genres=1,2",
        ),
        OpenApiParameter(
            "actors",
            type=OpenApiTypes.STR,
            description="Filter by actor IDs (comma separated). Ex: ?actors=1,2",
        ),
        OpenApiParameter(
            "title",
            type=OpenApiTypes.STR,
            description="Filter by movie title (case insensitive)",
        ),
    ]
)
class MovieViewSet(viewsets.ModelViewSet):
    queryset = Movie.objects.all()
    serializer_class = MovieSerializer
    # ... your existing get_queryset logic implementation


@extend_schema(
    parameters=[
        OpenApiParameter(
            "date",
            type=OpenApiTypes.DATE,
            description="Filter by date. Ex: ?date=2024-01-01",
        ),
        OpenApiParameter(
            "movie",
            type=OpenApiTypes.INT,
            description="Filter by movie ID",
        ),
    ]
)
class MovieSessionViewSet(viewsets.ModelViewSet):
    queryset = MovieSession.objects.all()
    serializer_class = MovieSessionSerializer
    # ... your existing get_queryset logic implementation
