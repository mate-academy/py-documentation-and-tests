from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

TOKEN_URL = reverse("user:login")
MOVIE_URL = reverse("cinema:movie-list")

class JWTAuthTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="test@example.com", password="testpass123"
        )

    def test_jwt_login_and_access(self):
        res = self.client.post(TOKEN_URL, {"email": "test@example.com", "password": "testpass123"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("access", res.data)
        self.assertIn("refresh", res.data)

        access_token = res.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        res2 = self.client.get(MOVIE_URL)
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
