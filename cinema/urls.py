# cinema/urls.py

from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from drf_spectacular.views import SpectacularAPIView

from .views import (
    ActorViewSet,
    GenreViewSet,
    MovieViewSet,
    MovieSessionViewSet,
)

app_name = "cinema"

router = DefaultRouter()
router.register("genres", GenreViewSet)
router.register("actors", ActorViewSet)
router.register("movies", MovieViewSet, basename="movie")
router.register("movie-sessions", MovieSessionViewSet)

urlpatterns = [
    # Endpoints da API
    path("", include(router.urls)),
    # JWT endpoints com nomes esperados pelos testes
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    # Endpoint público de schema para testes de throttling anônimo
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
]
