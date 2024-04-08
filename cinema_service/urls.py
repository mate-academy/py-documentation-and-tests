from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/cinema/", include("cinema.urls", namespace="cinema")),
    path("api/v1/user/", include("user.urls", namespace="user")),
    path("__debug__/", include("debug_toolbar.urls")),


    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/v1/doc/swagger/",
         SpectacularSwaggerView.as_view(url_name="schema"), name="swagger"),


] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
