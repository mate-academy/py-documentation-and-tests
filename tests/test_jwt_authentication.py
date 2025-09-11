from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class JWTAuthenticationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )

    def test_obtain_jwt_token(self):
        url = reverse("user:token_obtain_pair")
        payload = {"email": "test@example.com", "password": "testpass123"}
        res = self.client.post(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("access", res.data)
        self.assertIn("refresh", res.data)

    def test_obtain_jwt_token_invalid_credentials(self):
        url = reverse("user:token_obtain_pair")
        payload = {"email": "test@example.com", "password": "wrongpassword"}
        res = self.client.post(url, payload)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_jwt_token(self):
        refresh = RefreshToken.for_user(self.user)
        access_token = refresh.access_token

        url = reverse("user:token_refresh")
        payload = {"refresh": str(refresh)}
        res = self.client.post(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("access", res.data)

    def test_access_protected_endpoint_with_jwt(self):
        refresh = RefreshToken.for_user(self.user)
        access_token = refresh.access_token

        url = reverse("user:manage")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["email"], self.user.email)

    def test_access_protected_endpoint_without_jwt(self):
        url = reverse("user:manage")
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_access_protected_endpoint_with_invalid_jwt(self):
        url = reverse("user:manage")
        self.client.credentials(HTTP_AUTHORIZATION="Bearer invalid_token")
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
