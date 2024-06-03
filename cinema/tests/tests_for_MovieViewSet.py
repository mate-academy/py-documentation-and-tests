from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import Movie, Genre
from cinema.serializers import (
    MovieSerializer,
    MovieListSerializer,
    MovieDetailSerializer,
)
from cinema.tests.test_movie_api import detail_url

MOVIE_URL = reverse("cinema:movie-list")


def sample_movie(**params) -> Movie:
    defaults = {
        "title": "The Great Brick",
        "description": "The story",
        "duration": 120,
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
            email="test@test.com",
            password="TestPassword",
        )
        self.client.force_authenticate(self.user)

    def test_movie_list(self):
        sample_movie()
        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movie_by_title(self):
        movie1 = sample_movie(title="The Great Brick")
        movie2 = sample_movie(title="Another Story")
        movie3 = sample_movie(title="The Final Chapter")

        res = self.client.get(MOVIE_URL, {"title": "Great"})

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie3)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_retrieve_movie(self):
        movie = sample_movie()
        url = detail_url(movie.id)
        res = self.client.get(url)
        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "The Saw",
            "description": "Horror",
            "duration": 115,
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@admin.com",
            password="TestPassword",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        payload = {
            "title": "The Saw",
            "description": "Horror",
            "duration": 115,
        }
        res = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(pk=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_create_movie_with_genres(self):
        genre_1 = Genre.objects.create(name="Horror")
        genre_2 = Genre.objects.create(name="Drama")
        genre_3 = Genre.objects.create(name="Fantasy")
        payload = {
            "title": "The Saw",
            "description": "The Horrors story about man",
            "duration": 115,
            "genres": [genre_1.id, genre_2.id, genre_3.id],
        }
        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        movie = Movie.objects.get(pk=res.data["id"])
        genres = movie.genres.all()
        self.assertIn(genre_1, genres)
        self.assertIn(genre_2, genres)
        self.assertIn(genre_3, genres)
        self.assertEqual(genres.count(), 3)

    def test_delete_movie_not_allowed(self):
        movie = sample_movie()
        url = detail_url(movie.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
