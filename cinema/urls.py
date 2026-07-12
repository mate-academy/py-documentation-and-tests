from django.urls import path
from cinema.views import (
    GenreList,
    GenreDetail,
    ActorList,
    ActorDetail,
    CinemaHallList,
    CinemaHallDetail,
    MovieList,
    MovieDetail,
    MovieUploadImage,
    MovieSessionList,
    MovieSessionDetail,
    OrderList,
)

urlpatterns = [
    path("genres/", GenreList.as_view(), name="genre-list"),
    path("genres/<int:pk>/", GenreDetail.as_view(), name="genre-detail"),
    path("actors/", ActorList.as_view(), name="actor-list"),
    path("actors/<int:pk>/", ActorDetail.as_view(), name="actor-detail"),
    path("cinema_halls/", CinemaHallList.as_view(), name="cinemahall-list"),
    path("cinema_halls/<int:pk>/", CinemaHallDetail.as_view(), name="cinemahall-detail"),
    path("movies/", MovieList.as_view(), name="movie-list"),
    path("movies/<int:pk>/", MovieDetail.as_view(), name="movie-detail"),
    path("movies/<int:pk>/upload-image/", MovieUploadImage.as_view(), name="movie-upload-image"),
    path("movie_sessions/", MovieSessionList.as_view(), name="moviesession-list"),
    path("movie_sessions/<int:pk>/", MovieSessionDetail.as_view(), name="moviesession-detail"),
    path("orders/", OrderList.as_view(), name="order-list"),
]

app_name = "cinema"
