from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/user/", include(("user.urls", "user"),
                              namespace="user")),
    path("api/cinema/", include(("cinema.urls", "cinema"),
                                namespace="cinema")),
    path("api/schema/", SpectacularAPIView.as_view(),
         name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]
