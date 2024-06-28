from django.urls import path
from rest_framework_simplejwt.views import (
    TokenRefreshView,
    TokenObtainPairView,
    TokenVerifyView,
)

from user.views import CreateUserView, ManageUserView

app_name = "user"

urlpatterns = [
    path("register/", CreateUserView.as_view(), name="create"),
    path("token/", TokenObtainPairView.as_view(), name="taken_obtain_pairs"),
    path("token/refresh", TokenRefreshView.as_view(), name="taken_refresh"),
    path("token/verify", TokenVerifyView.as_view(), name="taken_verify"),
    path("me/", ManageUserView.as_view(), name="manage"),
]
