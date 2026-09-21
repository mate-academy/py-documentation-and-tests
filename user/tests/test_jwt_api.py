from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


class JwtAuthenticationTests(TestCase):
    def setUp(self):
        cache.clear()
        self.email = "jwt@example.com"
        self.password = "testpass123"
        self.user = get_user_model().objects.create_user(
            email=self.email,
            password=self.password,
        )
        self.client = APIClient()

    def obtain_tokens(self):
        return self.client.post(
            reverse("user:token_obtain_pair"),
            {"email": self.email, "password": self.password},
        )

    def test_obtain_jwt_pair_with_email_and_password(self):
        response = self.obtain_tokens()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_access_token_authenticates_profile_request(self):
        token_response = self.obtain_tokens()
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {token_response.data['access']}"
        )

        response = self.client.get(reverse("user:manage"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], self.email)

    def test_refresh_token_returns_new_access_token(self):
        token_response = self.obtain_tokens()

        response = self.client.post(
            reverse("user:token_refresh"),
            {"refresh": token_response.data["refresh"]},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
