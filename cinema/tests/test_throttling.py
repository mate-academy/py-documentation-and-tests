from django.contrib.auth import get_user_model
from rest_framework import status
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken


ANON_LIMIT = 10
AUTH_LIMIT = 30


class ThrottlingUnauthenticatedTests(TestCase):
    def setUp(self):
        AnonRateThrottle.cache.clear()
        self.client = APIClient()

    def test_authenticated_throttling(self):
        for i in range(ANON_LIMIT):
            res = self.client.get(reverse("user:create"))
            self.assertNotEqual(res.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

        res = self.client.get(reverse("user:create"))
        self.assertEqual(res.status_code, status.HTTP_429_TOO_MANY_REQUESTS)


class ThrottlingAuthenticatedTests(TestCase):
    def setUp(self):
        UserRateThrottle.cache.clear()
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@gmail.com",
            password="test_password",
        )
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)

    def test_authenticated_throttling(self):
        for i in range(AUTH_LIMIT):
            res = self.client.get(
                reverse("cinema:movie-list"),
                HTTP_AUTHORIZATION=f"Bearer {self.access_token}"
            )
            self.assertNotEqual(res.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

        res = self.client.get(
            reverse("cinema:movie-list"),
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}"
        )
        self.assertEqual(res.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
