from django.urls import path
from user.views import CreateUserView, CreateTokenView, ManageUserView
from rest_framework_simplejwt.views import TokenRefreshView


app_name = "user"

urlpatterns = [
    path("register/", CreateUserView.as_view(), name="create"),
    path("token/", CreateTokenView.as_view(), name="login"),
    path("me/", ManageUserView.as_view(), name="manage"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]
