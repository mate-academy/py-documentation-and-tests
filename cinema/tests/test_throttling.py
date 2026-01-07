from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import status
from django.core.cache import cache

MOVIE_URL = reverse("cinema:movie-list")

class ThrottlingTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="user@test.com", password="testpass"
        )

    def test_anon_user_throttle(self):
        cache.clear()
        
        for i in range(11):
            if i < 10:
                res = self.client.get(MOVIE_URL)
                self.assertIn(res.status_code, [status.HTTP_200_OK])
            else:
                res = self.client.get(MOVIE_URL)
                self.assertIn(res.status_code,
                              [status.HTTP_429_TOO_MANY_REQUESTS])

    def test_authenticated_user_throttle(self):
        cache.clear()
        
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer "
                                                   f"{refresh.access_token}")
        for i in range(31):
            if i < 30:
                res = self.client.get(MOVIE_URL)
                self.assertIn(res.status_code, [status.HTTP_200_OK])
            else:
                res = self.client.get(MOVIE_URL)
                self.assertIn(res.status_code,
                              [status.HTTP_429_TOO_MANY_REQUESTS])
                