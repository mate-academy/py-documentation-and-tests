from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.cache import cache
from rest_framework.test import APIClient
from rest_framework import status
from django.conf import settings


def obtain_access_token(client: APIClient, email: str, password: str) -> str:
    resp = client.post(
        reverse("token_obtain_pair"),
        {"email": email, "password": password},
        format="json",
    )
    assert resp.status_code == status.HTTP_200_OK, resp.data
    return resp.data["access"]


class ThrottlingTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        cache.clear()
        self.list_url = reverse("cinema:movie-list")

    def tearDown(self) -> None:
        cache.clear()

    def test_authenticated_is_limited(self) -> None:
        email = "user@example.com"
        password = "testpass123"
        get_user_model().objects.create_user(email=email, password=password)
        access = obtain_access_token(self.client, email, password)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

        for _ in range(30):
            r = self.client.get(self.list_url)
            self.assertNotEqual(r.status_code, status.HTTP_429_TOO_MANY_REQUESTS, r.data)

        r = self.client.get(self.list_url)
        self.assertEqual(r.status_code, status.HTTP_429_TOO_MANY_REQUESTS)