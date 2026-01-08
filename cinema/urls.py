from django.urls import path, include
from rest_framework.routers import DefaultRouter
from cinema import views


app_name = "cinema"

router = DefaultRouter()
router.register("genres", views.GenreViewSet, basename="genre")
router.register("actors", views.ActorViewSet, basename="actor")
router.register("cinema_halls",
                views.CinemaHallViewSet,
                basename="cinemahall")
router.register("movies", views.MovieViewSet, basename="movie")
router.register("movie_sessions",
                views.MovieSessionViewSet,
                basename="moviesession")
router.register("orders", views.OrderViewSet, basename="order")

urlpatterns = [path("", include(router.urls))]
