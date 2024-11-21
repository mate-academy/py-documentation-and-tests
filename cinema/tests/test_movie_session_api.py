from django.test import TestCase
from django.contrib.auth import get_user_model

from rest_framework.test import APIClient
from rest_framework.reverse import reverse
from rest_framework import status

from cinema.models import Movie, Genre
from cinema.serializers import MovieListSerializer

MOVIE_URL = reverse("cinema:movie-list")


def sample_movie(**params) -> Movie:
    defaults = {
        "title": "Groundhog Day",
        "description": "A narcissistic, self-centered weatherman finds himself in a time loop on Groundhog Day.",
        "duration": "101",
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)


class UnauthenticatedCinemaApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedCinemaApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@test.com",
            password="testpassword"
        )
        self.client.force_authenticate(self.user)

    def test_movie_list(self):
        sample_movie()
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)
        res = self.client.get(MOVIE_URL)
        self.assertTrue(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_movie_by_genre(self):
        sample_movie(
            title="test title",
            description="test description",
            duration=100
        )
        genre_1 = Genre.objects.create(name="Comedy")
        genre_2 = Genre.objects.create(name="Drama")
        genre_3 = Genre.objects.create(name="Fantasy")
        genre_4 = Genre.objects.create(name="Romance")
        sample_movie_with_genres = sample_movie()
        sample_movie_with_genres.genres.add(
            genre_1,
            genre_2,
            genre_3,
            genre_4,
        )
        sample_movie_with_genres.save()
