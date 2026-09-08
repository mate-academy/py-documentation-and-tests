from django.urls import path, include
from rest_framework import routers

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)
from .views import (
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

urlpatterns = [
    path("", include(router.urls)),
    path("", include(router.urls)),
    path(
        "api/token/",
        TokenObtainPairView.as_view(),
        name="token_obtain_pair"
    ),
    path(
        "api/token/refresh/",
        TokenRefreshView.as_view(),
        name="token_refresh"
    ),
    path("api/token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "doc/swagger/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]

app_name = "cinema"
