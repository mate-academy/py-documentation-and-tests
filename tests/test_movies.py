from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from cinema.models import Movie, Genre, Actor
from user.models import User


class MovieViewSetTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@test.com", password="pass1234"
        )
        refresh = RefreshToken.for_user(self.user)
        self.token = str(refresh.access_token)

        self.genre = Genre.objects.create(name="Action")
        self.actor = Actor.objects.create(first_name="John", last_name="Doe")
        self.movie = Movie.objects.create(
            title="Test Movie", description="Desc", duration=120
        )
        self.movie.genres.add(self.genre)
        self.movie.actors.add(self.actor)

        self.url = reverse("cinema:movie-list")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

    def test_list_movies_unauthorized(self):
        self.client.credentials()  # скидаємо токен
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_movies_authorized(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_filter_movies_by_title(self):
        response = self.client.get(self.url, {"title": "Test"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Test Movie")

    def test_filter_movies_by_genre(self):
        response = self.client.get(self.url, {"genres": str(self.genre.id)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertIn("Action", response.data[0]["genres"])

    def test_filter_movies_by_actor(self):
        response = self.client.get(self.url, {"actors": str(self.actor.id)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertIn("John Doe", response.data[0]["actors"])
