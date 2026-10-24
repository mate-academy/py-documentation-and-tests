from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient


class JwtAndThrottlingTests(TestCase):
    def setUp(self) -> None:
        cache.clear()
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user@example.com", password="password"
        )

    def test_login_refresh_verify_and_authenticated_request(self) -> None:
        response = self.client.post(
            reverse("user:login"),
            {"email": self.user.email, "password": "password"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        refresh = response.data["refresh"]
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {response.data['access']}"
        )
        response = self.client.get(reverse("user:manage"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["email"], self.user.email)
        self.client.credentials()
        response = self.client.post(
            reverse("user:token-refresh"), {"refresh": refresh}
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.post(
            reverse("user:token-verify"), {"token": response.data["access"]}
        )
        self.assertEqual(response.status_code, 200)

    def test_invalid_credentials_and_token(self) -> None:
        response = self.client.post(
            reverse("user:login"),
            {"email": self.user.email, "password": "wrong"},
        )
        self.assertEqual(response.status_code, 401)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer invalid")
        self.assertEqual(
            self.client.get(reverse("user:manage")).status_code, 401
        )
        self.client.credentials()
        response = self.client.post(
            reverse("user:token-refresh"), {"refresh": "invalid"}
        )
        self.assertEqual(response.status_code, 401)

    def test_anonymous_limit_is_ten_requests_per_minute(self) -> None:
        url = reverse("user:create")
        for _ in range(10):
            self.assertEqual(self.client.get(url).status_code, 405)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 429)
        self.assertIn("Retry-After", response)

    def test_authenticated_limit_is_thirty_requests_per_minute(self) -> None:
        self.client.force_authenticate(self.user)
        url = reverse("cinema:genre-list")
        for _ in range(30):
            self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.get(url).status_code, 429)
