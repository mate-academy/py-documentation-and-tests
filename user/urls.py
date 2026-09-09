from django.urls import path
from drf_spectacular.utils import extend_schema_view, extend_schema
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from user.views import CreateUserView, ManageUserView

app_name = "user"

urlpatterns = [
    path("register/", CreateUserView.as_view(), name="create"),
    path(
        "token/",
        extend_schema_view(
            post=extend_schema(summary="Obtain JWT access and refresh token")
        )(TokenObtainPairView).as_view(),
        name="token_obtain_pair"
    ),
    path(
        "token/refresh/",
        extend_schema_view(
            post=extend_schema(summary="Refresh JWT access token")
        )(TokenRefreshView).as_view(),
        name="token_refresh"
    ),
    path("me/", ManageUserView.as_view(), name="manage"),
]
