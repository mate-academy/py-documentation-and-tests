from django.urls import path, include
from rest_framework import routers

from cinema.views import (
    GenreViewSet,
    ActorViewSet,
    CinemaHallViewSet,
    MovieViewSet,
    MovieSessionViewSet,
    OrderViewSet,
)

router = routers.DefaultRouter()
router.register("genres", GenreViewSet, basename="genre")
router.register("actors", ActorViewSet, basename="actor")
router.register("cinema_halls", CinemaHallViewSet, basename="cinemahall")
router.register("movies", MovieViewSet, basename="movie")
router.register(
    "movie_sessions",
    MovieSessionViewSet,
    basename="moviesession"
)
router.register("orders", OrderViewSet, basename="order")

urlpatterns = [path("", include(router.urls))]

app_name = "cinema"
