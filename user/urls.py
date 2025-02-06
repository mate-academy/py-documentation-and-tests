from django.urls import path
from user.views import CreateUserView, CreateTokenView, ManageUserView
from rest_framework.authtoken.views import ObtainAuthToken

app_name = "user"

urlpatterns = [
    path("login/", ObtainAuthToken.as_view(), name="login"),
    path("register/", CreateUserView.as_view(), name="create"),
    path("token/", CreateTokenView.as_view(), name="token"),
    path("me/", ManageUserView.as_view(), name="manage"),
]
