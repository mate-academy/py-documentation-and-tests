# user/urls.py

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import MovieViewSet

app_name = "user"

router = DefaultRouter()
router.register("movies", MovieViewSet, basename="movie")

urlpatterns = [
    path("", include(router.urls)),
]
