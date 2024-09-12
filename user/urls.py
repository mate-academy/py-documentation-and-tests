from django.urls import path

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from user.views import ManageUserView


urlpatterns = [
    path("me/", ManageUserView.as_view(), name="manage"),
    path("token_obtain/", TokenObtainPairView.as_view(), name="token_obtain"),
    path("token_refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]

app_name = "user"
