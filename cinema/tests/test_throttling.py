from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse, path
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.test import APIClient


class MockOpenView(APIView):
    permission_classes = []

    def get(self, request):
        return Response({"status": "open"})


urlpatterns = [
    path("api/open-test/", MockOpenView.as_view(), name="mock-open"),
]


@override_settings(ROOT_URLCONF=__name__)
class ThrottlingTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user@cinema.com", password="password123"
        )
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_anon_throttle_rate_limits_at_11th_request(self):
        """Anon user limits at 10 requests"""
        url = reverse("mock-open")

        for _ in range(10):
            res = self.client.get(url)
            self.assertEqual(res.status_code, status.HTTP_200_OK)

        final_res = self.client.get(url)
        self.assertEqual(
            final_res.status_code, status.HTTP_429_TOO_MANY_REQUESTS
        )

    @override_settings(ROOT_URLCONF="cinema_service.urls")
    def test_auth_throttle_rate_limits_at_31st_request(self):
        """Auth user limits at 30 requests"""
        self.client.force_authenticate(self.user)
        # Перенесено обчислення URL всередину методу
        movie_url = reverse("cinema:movie-list")

        for _ in range(30):
            res = self.client.get(movie_url)
            self.assertEqual(res.status_code, status.HTTP_200_OK)

        final_res = self.client.get(movie_url)
        self.assertEqual(
            final_res.status_code, status.HTTP_429_TOO_MANY_REQUESTS
        )
