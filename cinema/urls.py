from django.urls import path, include
from rest_framework.routers import DefaultRouter
from cinema.views import MovieViewSet, MovieSessionViewSet

app_name = "cinema"

router = DefaultRouter()
router.register("movies", MovieViewSet)
router.register("moviesessions", MovieSessionViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
