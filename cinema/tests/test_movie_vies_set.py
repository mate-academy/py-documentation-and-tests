from django.contrib.auth import get_user_model
from django.contrib.sites import requests
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from cinema.models import Movie, Genre
from cinema.serializers import MovieSerializer, MovieListSerializer, MovieDetailSerializer
from cinema.tests.test_movie_api import MOVIE_URL

MOVIE_URL = reverse("cinema:movie-list")

def detail_url(movie_id):
    return reverse("cinema:movie-detail", args={movie_id,})

def sample_movie(**params) -> Movie:
    defaults = {
        "title": "Test Movie",
        "description": "Test Movie Description",
        "duration": 60,
    }
    defaults.update(params)

    return Movie.objects.create(**defaults)


class UnauthenticatedMovieApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(MOVIE_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.test", password="test123"
        )
        self.client.force_authenticate(self.user)

    def test_movies_list(self):
        sample_movie()

        movie_with_genres = sample_movie()

        genre_1 = Genre.objects.create(name="Test Genre")
        genre_2 = Genre.objects.create(name="Test Genre2")

        movie_with_genres.genres.add(genre_1, genre_2)

        response = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.data, serializer.data)

    def test_filter_movies_by_genres(self):
        movie_without_genres = sample_movie()
        movie_with_genres_1 = sample_movie(title="Test Movie")
        movie_with_genres_2 = sample_movie(title="Test Movie2")

        genre_1 = Genre.objects.create(name="Test Genre")
        genre_2 = Genre.objects.create(name="Test Genre2")

        movie_with_genres_1.genres.add(genre_1)
        movie_with_genres_2.genres.add(genre_2)

        res = self.client.get(
            MOVIE_URL,
            {"genres": f"{genre_1.id},{genre_2.id}"},

        )
        serializer_without_genres = MovieListSerializer(movie_without_genres)
        serializer_movie_genre_1 = MovieListSerializer(movie_with_genres_1)
        serializer_movie_genre_2 = MovieListSerializer(movie_with_genres_2)

        self.assertIn(serializer_movie_genre_1.data, res.data)
        self.assertIn(serializer_movie_genre_2.data, res.data)
        self.assertNotIn(serializer_without_genres.data, res.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        movie.genres.add(Genre.objects.create(name="Test Genre"))

        url = detail_url(movie.id)

        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Test Movie",
            "description": "Test Movie Description"
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@admin.test", password="test123", is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        payload = {
            "title": "Test Movie",
            "description": "Test Movie Description",
            "duration": 60,
        }

        res = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        for key in payload.keys():
            self.assertEqual(payload[key], getattr(movie, key))

    def test_create_movie_with_genre(self):
        genre_1 = Genre.objects.create(name="Test Genre")
        genre_2 = Genre.objects.create(name="Test Genre2")
        payload = {
            "title": "Test Movie",
            "description": "Test Movie Description",
            "duration": 60,
            "genres": [genre_1.id, genre_2.id]
        }

        res = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(id=res.data["id"])
        genres = movie.genres.all()
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn(genre_1, genres)
        self.assertIn(genre_2, genres)
        self.assertEqual(genres.count(), 2)

    def test_delete_movie_not_allowed(self):
        movie = sample_movie()

        url = detail_url(movie.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
