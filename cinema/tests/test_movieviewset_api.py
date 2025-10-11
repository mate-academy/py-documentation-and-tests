from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from cinema.models import Movie
from cinema.serializers import MovieSerializer

MOVIE_URL = reverse("cinema:movie-list")

def sample_movie(**params):
    defaults = {
        "title": "test_movie",
        "duration": 111,
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)


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
            email="test@test.test",
            password="testpassword"
        )
        self.client.force_authenticate(self.user)

    def test_movie_list(self):
        sample_movie()

        res = self.client.get(MOVIE_URL)
        movie = Movie.objects.all()
        serializer = MovieSerializer(movie, many=True)
        self.assertEqual(res.data, serializer.data)


