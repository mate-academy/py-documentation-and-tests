from django.urls import path

from user.views import CreateUserView, ManageUserView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

app_name = "user"

urlpatterns = [
    path(
        "register/",
        CreateUserView.as_view(),
        name="create"
    ),
    path(
        "me/",
        ManageUserView.as_view(),
        name="manage"
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

]
