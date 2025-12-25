# views.py
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from rest_framework import viewsets
from .models import Movie
from .serializers import MovieSerializer, MovieListSerializer, MovieDetailSerializer

class MovieViewSet(viewsets.ModelViewSet):
    queryset = Movie.objects.all()
    # Assuming you have specific serializers for list/detail
    def get_serializer_class(self):
        if self.action == 'list':
            return MovieListSerializer
        if self.action == 'retrieve':
            return MovieDetailSerializer
        return MovieSerializer

    def get_queryset(self):
        """Retrieve the movies with filters."""
        queryset = self.queryset
        
        # Filtering logic
        title = self.request.query_params.get('title')
        genres = self.request.query_params.get('genres')
        actors = self.request.query_params.get('actors')

        if title:
            queryset = queryset.filter(title__icontains=title)
        if genres:
            # Assuming comma separated IDs or names, e.g. ?genres=1,2
            genres_ids = [int(str_id) for str_id in genres.split(",")]
            queryset = queryset.filter(genres__id__in=genres_ids)
        if actors:
            actors_ids = [int(str_id) for str_id in actors.split(",")]
            queryset = queryset.filter(actors__id__in=actors_ids)

        return queryset.distinct()

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='title',
                description='Filter by movie title (insensitive contains)',
                required=False,
                type=OpenApiTypes.STR,
            ),
            OpenApiParameter(
                name='genres',
                description='Filter by genre IDs (comma-separated, e.g. 1,2)',
                required=False,
                type={'type': 'array', 'items': {'type': 'number'}},
            ),
            OpenApiParameter(
                name='actors',
                description='Filter by actor IDs (comma-separated, e.g. 1,2)',
                required=False,
                type={'type': 'array', 'items': {'type': 'number'}},
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
