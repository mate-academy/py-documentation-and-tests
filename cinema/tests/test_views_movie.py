from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from cinema.models import Movie, Genre, Actor


class MovieViewSetTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            email="test@gmail.com",
            password="testpassword123"
        )

        cls.admin = get_user_model().objects.create_superuser(
            email="admin@gmail.com",
            password="adminpass123"
        )

        cls.genre = Genre.objects.create(name="Action")
        cls.actor = Actor.objects.create(first_name="John", last_name="Doe")

        cls.movie = Movie.objects.create(
            title="Movie One", description="First movie", duration=120
        )
        cls.movie.genres.add(cls.genre)
        cls.movie.actors.add(cls.actor)

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_list_movies(self):
        url = reverse("cinema:movie-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Movie One")

    def test_retrieve_movie(self):
        url = reverse("cinema:movie-detail", args=[self.movie.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], self.movie.title)

    def test_filter_movies_by_title(self):
        url = reverse("cinema:movie-list")
        response = self.client.get(url, {"title": "Movie One"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Movie One")
