from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, \
    SpectacularRedocView


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/cinema/", include("cinema.urls", namespace="cinema")),
    path("api/user/", include("user.urls", namespace="user")),
    path("__debug__/", include("debug_toolbar.urls")),
    path("api/doc/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/doc/swagger/", SpectacularSwaggerView.as_view(),
        name="swagger-ui"
    ),
    path(
        "api/doc/redoc/", SpectacularRedocView.as_view(),
        name="redoc-ui"
    ),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
