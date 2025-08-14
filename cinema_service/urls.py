from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView



urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/cinema/", include("cinema.urls", namespace="cinema")),
    path("api/user/", include("user.urls", namespace="user")),
    path("__debug__/", include("debug_toolbar.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += [
   path("api/doc/", SpectacularAPIView.as_view(), name="schema"),
   path("api/doc/swagger/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
   path("api/doc/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]
from rest_framework_simplejwt.views import (
   TokenObtainPairView,
   TokenRefreshView,
)

urlpatterns += [
   path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
   path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]