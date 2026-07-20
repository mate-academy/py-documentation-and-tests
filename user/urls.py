from django.urls import path
from user.views import (
    MyTokenObtainPairView,
    MyTokenRefreshView,
    MyTokenVerifyView,
    CreateUserView,
    ManageUserView
)


app_name = "user"

urlpatterns = [
    path("register/", CreateUserView.as_view(), name="create"),
    path("token/verify/", MyTokenVerifyView.as_view(), name="token_verify"),
    path("token/", MyTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", MyTokenRefreshView.as_view(), name="token_refresh"),
    path("me/", ManageUserView.as_view(), name="manage"),
]
