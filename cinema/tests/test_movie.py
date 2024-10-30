from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from cinema.models import Movie
from cinema.serializers import MovieSerializer
from cinema.tests.test_movie_api import MOVIE_URL
MOVIE_URL = reverse("cinema:movie-list")


def sample_movie(genres=None, actors=None, **params):
    defaults = {
        "title": "Inception",
        "description": "The inception",
        "duration": "60",
    }
    defaults.update(params)
    movie = Movie.objects.create(**defaults)
    if genres:
        movie.genres.set(genres)
    if actors:
        movie.actors.set(actors)
    return movie

class UnauthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com",
            password="testpass"
        )
        self.client.force_authenticate(self.user)

    def test_list_movies(self):
        sample_movie()
        res = self.client.get(MOVIE_URL)

        movies = Movie.objects.all()
        self.assertEqual(res.status_code, status.HTTP_200_OK)

