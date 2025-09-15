from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

from cinema.models import Movie, Genre, Actor


class TestMovieViewSet(TestCase):
    def setUp(self):
        self.admin_user = get_user_model().objects.create_superuser(
            email="admin@example.com", password="adminpass"
        )
        self.user = get_user_model().objects.create_user(
            email="user@example.com", password="userpass"
        )
        self.genre = Genre.objects.create(name="Action")
        self.actor = Actor.objects.create(first_name="John", last_name="Doe")
        self.movie = Movie.objects.create(
            title="Test Movie",
            description="Test Description",
            duration=120,
        )
        self.movie.genres.add(self.genre)
        self.movie.actors.add(self.actor)
        self.api_client = APIClient()
        self.admin_client = APIClient()
        self.admin_client.force_authenticate(self.admin_user)
        self.user_client = APIClient()
        self.user_client.force_authenticate(self.user)
        self.list_url = reverse("cinema:movie-list")

    def test_list_movies(self):
        res = self.user_client.get(self.list_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data[0]["title"], self.movie.title)

    def test_retrieve_movie(self):
        url = reverse("cinema:movie-detail", args=[self.movie.id])
        res = self.user_client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["title"], self.movie.title)

    def test_create_movie_admin(self):
        payload = {
            "title": "New Movie",
            "description": "Desc",
            "duration": 100,
            "genres": [self.genre.id],
            "actors": [self.actor.id],
        }
        res = self.admin_client.post(self.list_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Movie.objects.filter(title="New Movie").exists())

    def test_create_movie_user_forbidden(self):
        payload = {
            "title": "User Movie",
            "description": "Desc",
            "duration": 90,
            "genres": [self.genre.id],
            "actors": [self.actor.id],
        }
        res = self.user_client.post(self.list_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
