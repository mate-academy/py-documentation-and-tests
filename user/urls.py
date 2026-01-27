from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from user.views import CreateUserView, CreateTokenView, ManageUserView

app_name = "user"

urlpatterns = [
    path("register/", CreateUserView.as_view(), name="create"),
    path("login/", CreateTokenView.as_view(), name="login"),
    path("me/", ManageUserView.as_view(), name="manage"),
    path("token/jwt/", TokenObtainPairView.as_view(), name="jwt-token"),
    path(
        "token/jwt/refresh/",
        TokenRefreshView.as_view(),
        name="jwt-refresh",
    ),
]
