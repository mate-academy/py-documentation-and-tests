from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


class JwtAuthenticationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.email = "user@example.com"
        self.password = "testpass123"
        get_user_model().objects.create_user(
            email=self.email,
            password=self.password,
        )

    def test_obtain_and_refresh_jwt(self):
        token_response = self.client.post(
            reverse("user:token_obtain_pair"),
            {"email": self.email, "password": self.password},
        )

        self.assertEqual(token_response.status_code, status.HTTP_200_OK)
        self.assertIn("access", token_response.data)
        self.assertIn("refresh", token_response.data)

        refresh_response = self.client.post(
            reverse("user:token_refresh"),
            {"refresh": token_response.data["refresh"]},
        )

        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
        self.assertIn("access", refresh_response.data)

    def test_access_protected_endpoint_with_jwt(self):
        token_response = self.client.post(
            reverse("user:token_obtain_pair"),
            {"email": self.email, "password": self.password},
        )
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {token_response.data['access']}"
        )

        response = self.client.get(reverse("user:manage"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], self.email)

