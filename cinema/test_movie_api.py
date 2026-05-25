from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

MOVIE_URL = reverse("cinema:movie-list")


class PublicMovieApiTests(APITestCase):
    def test_auth_required(self):
        response = self.client.get(MOVIE_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateMovieApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="user@test.com", password="password123"
        )
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}"
        )

    def test_list_movies(self):
        response = self.client.get(MOVIE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_movie_forbidden(self):
        payload = {"title": "Interstellar", "duration": 169}
        response = self.client.post(MOVIE_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
