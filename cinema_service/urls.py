# cinema_service/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
                  path("admin/", admin.site.urls),
                  # Inclusão do namespace 'cinema'
                  path("api/cinema/", include("cinema.urls", namespace="cinema")),
                  # Inclusão do namespace 'user' (para JWT)
                  path("api/user/", include("user.urls", namespace="user")),

                  # Debug Toolbar
                  path("__debug__/", include("debug_toolbar.urls")),

                  # SWAGGER URLs
                  path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
                  path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
              ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
