from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

MOVIE_URL = reverse("cinema:movie-list")


class ApiDocumentationTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()

    def test_schema_contains_documented_filter_parameters(self):
        response = self.client.get(reverse("api-schema"))
        schema = response.content.decode()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for parameter in ("title", "genres", "actors", "date", "movie"):
            self.assertIn(f"name: {parameter}", schema)
        self.assertIn("Filter movies by title", schema)
        self.assertIn("Filter sessions by date", schema)
        self.assertIn("jwtAuth", schema)

    def test_swagger_page_is_available(self):
        response = self.client.get(reverse("api-docs"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ThrottlingTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()

    def tearDown(self):
        cache.clear()

    def test_anonymous_requests_are_limited_to_ten_per_minute(self):
        url = reverse("user:create")

        responses = [self.client.get(url) for _ in range(11)]

        self.assertNotEqual(
            responses[9].status_code,
            status.HTTP_429_TOO_MANY_REQUESTS,
        )
        self.assertEqual(
            responses[10].status_code,
            status.HTTP_429_TOO_MANY_REQUESTS,
        )

    def test_authenticated_requests_are_limited_to_thirty_per_minute(self):
        user = get_user_model().objects.create_user(
            email="throttle@example.com",
            password="testpass123",
        )
        self.client.force_authenticate(user)

        responses = [self.client.get(MOVIE_URL) for _ in range(31)]

        self.assertEqual(responses[29].status_code, status.HTTP_200_OK)
        self.assertEqual(
            responses[30].status_code,
            status.HTTP_429_TOO_MANY_REQUESTS,
        )
