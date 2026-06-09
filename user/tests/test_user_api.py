from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


class JwtAuthenticationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.password = "testpass123"
        self.user = get_user_model().objects.create_user(
            email="jwt.user@cinema.com",
            password=self.password,
        )

    def test_obtain_and_refresh_jwt(self):
        token_response = self.client.post(
            reverse("user:token_obtain_pair"),
            {
                "email": self.user.email,
                "password": self.password,
            },
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

    def test_access_token_authenticates_request(self):
        token_response = self.client.post(
            reverse("user:token_obtain_pair"),
            {
                "email": self.user.email,
                "password": self.password,
            },
        )
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {token_response.data['access']}"
        )

        response = self.client.get(reverse("cinema:movie-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ThrottlingTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()

    def tearDown(self):
        cache.clear()

    def test_anonymous_requests_are_limited_to_ten_per_minute(self):
        url = reverse("user:create")

        for index in range(10):
            response = self.client.post(
                url,
                {
                    "email": f"anonymous{index}@cinema.com",
                    "password": "testpass123",
                },
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = self.client.post(
            url,
            {
                "email": "limited@cinema.com",
                "password": "testpass123",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_429_TOO_MANY_REQUESTS,
        )

    def test_authenticated_requests_are_limited_to_thirty_per_minute(self):
        user = get_user_model().objects.create_user(
            email="throttled.user@cinema.com",
            password="testpass123",
        )
        self.client.force_authenticate(user)
        url = reverse("cinema:movie-list")

        for _ in range(30):
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_429_TOO_MANY_REQUESTS,
        )
