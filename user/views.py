# user/views.py

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import viewsets

from cinema.models import Movie
from cinema.serializers import (
    MovieDetailSerializer,
    MovieImageSerializer,
    MovieListSerializer,
)
from cinema.permissions import IsAdminOrIfAuthenticatedReadOnly


@extend_schema(
    tags=["Movies"],
    summary="Operações com filmes (user API)",
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
    """
    ViewSet de filmes exposto via user app.
    Permite listagem, detalhe e operações de escrita
    (restritas a staff via IsAdminOrIfAuthenticatedReadOnly).
    """

    queryset = Movie.objects.prefetch_related("genres", "actors")
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    def get_serializer_class(self):
        if self.action == "list":
            return MovieListSerializer
        if self.action == "upload_image":
            return MovieImageSerializer
        return MovieDetailSerializer

    def get_queryset(self):
        qs = self.queryset
        title = self.request.query_params.get("title")
        genres = self.request.query_params.get("genres")
        actors = self.request.query_params.get("actors")

        if title:
            qs = qs.filter(title__icontains=title)

        if genres:
            try:
                genre_ids = [int(g) for g in genres.split(",") if g.strip()]
                qs = qs.filter(genres__id__in=genre_ids)
            except ValueError:
                pass

        if actors:
            try:
                actor_ids = [int(a) for a in actors.split(",") if a.strip()]
                qs = qs.filter(actors__id__in=actor_ids)
            except ValueError:
                pass

        return qs.distinct()
