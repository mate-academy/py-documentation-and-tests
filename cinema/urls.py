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


app_name = "cinema"

router = routers.DefaultRouter()
router.register("genres", GenreViewSet)
router.register("actors", ActorViewSet)
router.register("cinema_halls", CinemaHallViewSet)
router.register("movies", MovieViewSet, basename="movies")
router.register("movie_sessions", MovieSessionViewSet, basename="movie_sessions")
router.register("orders", OrderViewSet)


urlpatterns = [path("", include(router.urls))]
