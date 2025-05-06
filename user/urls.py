from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from user.views import ManageUserView

app_name = "user"

urlpatterns = [
    path(
        "token/", TokenObtainPairView.as_view(), name="token_obtain_pair"
    ),
    path(
        "token/refresh/", TokenRefreshView.as_view(), name="token_refresh"
    ),
    path("me/", ManageUserView.as_view(), name="manage"),
]
