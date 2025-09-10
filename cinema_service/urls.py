from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView
)
from rest_framework.permissions import AllowAny

urlpatterns = [
    path("admin/", admin.site.urls),

    path(
        "api/cinema/",
        include(("cinema.urls", "cinema"), namespace="cinema")
    ),
    path(
        "api/user/",
        include(("user.urls", "user"), namespace="user")
    ),

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

    path(
        "api/schema/",
        SpectacularAPIView.as_view(permission_classes=[AllowAny]),
        name="schema"
    ),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui"
    ),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
