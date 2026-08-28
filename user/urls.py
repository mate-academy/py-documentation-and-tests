from django.urls import path

from user.views import (
    CreateUserView,
    CustomTokenObtainPairView,
    CustomTokenRefreshView,
    CustomTokenVerifyView,
    ManageUserView,
)

app_name = "user"

urlpatterns = [
    path("register/", CreateUserView.as_view(), name="create"),
    path(
        "token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"
    ),
    path(
        "token/refresh/",
        CustomTokenRefreshView.as_view(),
        name="token_refresh",
    ),
    path(
        "token/verify/", CustomTokenVerifyView.as_view(), name="token_verify"
    ),
    path("me/", ManageUserView.as_view(), name="manage"),
]
