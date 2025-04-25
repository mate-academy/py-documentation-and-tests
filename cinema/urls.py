from django.urls import path, include
from rest_framework import routers
from drf_spectacular.utils import extend_schema, OpenApiParameter

from cinema.views import (
    GenreViewSet,
    ActorViewSet,
    CinemaHallViewSet,
    MovieViewSet,
    MovieSessionViewSet,
    OrderViewSet,
)

router = routers.DefaultRouter()
router.register("genres", GenreViewSet)
router.register("actors", ActorViewSet)
router.register("cinema_halls", CinemaHallViewSet)
router.register("movies", MovieViewSet)
router.register("movie_sessions", MovieSessionViewSet)
router.register("orders", OrderViewSet)


@extend_schema(
    description="Cinema API endpoints for managing genres, actors, cinema halls, "
    "movies, movie sessions and orders",
    tags=["Cinema API"],
)
class CinemaAPIRootView(routers.APIRootView):
    pass


router.APIRootView = CinemaAPIRootView

urlpatterns = [path("", include(router.urls))]

app_name = "cinema"
