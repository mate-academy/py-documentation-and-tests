from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/cinema/", include("cinema.urls", namespace="cinema")),
    path("api/user/", include("user.urls", namespace="user")),

    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    # Шлях для схеми OpenAPI
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),  # Додає основну схему API

    # Шлях для Swagger UI
    path("swagger/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    # Swagger UI документація

    # Шлях для Redoc
    path("redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),  # ReDoc документація

    path("__debug__/", include("debug_toolbar.urls")),
    ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
