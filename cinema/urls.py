from django.urls import path, include
from rest_framework.routers import DefaultRouter

from cinema.views import (
    GenreViewSet,
    ActorViewSet,
    CinemaHallViewSet,
    MovieViewSet,
    MovieSessionViewSet,
    OrderViewSet,
)

router = DefaultRouter()
router.register("genres", GenreViewSet)
router.register("actors", ActorViewSet)
router.register("cinema-halls", CinemaHallViewSet)
router.register("movies", MovieViewSet)
router.register("movie-sessions", MovieSessionViewSet)
router.register("orders", OrderViewSet)

app_name = "cinema"

urlpatterns = [
    path("", include(router.urls)),
]
