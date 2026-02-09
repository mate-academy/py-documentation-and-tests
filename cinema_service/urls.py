from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/cinema/", include("cinema.urls", namespace="cinema")),
    path("api/user/", include("user.urls", namespace="user")),
    path("__debug__/", include("debug_toolbar.urls")),
    path(
        "api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"
    ),  # noqa 501
    path(
        "api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"
    ),  # noqa 501
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),  # noqa 501
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
