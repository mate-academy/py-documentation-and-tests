from django.contrib.auth import get_user_model
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient
from django.urls import reverse

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")
MOVIE_SESSION_URL = reverse("cinema:moviesession-list")


def sample_movie(**params):
    defaults = {
        "title": "TestTitle",
        "description": "Test descr",
        "duration": 10,
    }

    defaults.update(params)

    return Movie.objects.create(**defaults)


def create_test_movies():
    genre1 = Genre.objects.create(name="genre1")
    genre2 = Genre.objects.create(name="genre2")

    actor1 = Actor.objects.create(first_name="First", last_name="Test")
    actor2 = Actor.objects.create(first_name="Second", last_name="Test")

    movie_with_genres = sample_movie()
    movie_with_actors = sample_movie()

    movie_with_actors.actors.add(actor1, actor2)
    movie_with_genres.genres.add(genre1, genre2)


def detail_url(pk):
    return reverse("cinema:movie-detail", args=[pk])


class TestMovieUnauthenticated(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class TestMovieUserAuthenticated(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@test.com",
            "testpass"
        )
        self.client.force_authenticate(self.user)

    def test_list_movies(self):
        create_test_movies()

        res = self.client.get(MOVIE_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_movies_with_filters(self):
        create_test_movies()
        sample_movie(title="Hello, World!")

        res = self.client.get(MOVIE_URL, {"title": "Test"})

        serializer1 = MovieListSerializer(Movie.objects.get(id=1), many=False)
        serializer2 = MovieListSerializer(Movie.objects.get(id=2), many=False)
        serializer3 = MovieListSerializer(Movie.objects.get(id=3), many=False)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

        res = self.client.get(MOVIE_URL, {"genres": [1, 2]})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

        res = self.client.get(MOVIE_URL, {"actors": [1, 2]})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertNotIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        movie.genres.add(Genre.objects.create(name="Test"))

        url = detail_url(movie.id)
        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Movie",
            "description": "Description",
            "duration": 10,
        }

        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

class MovieImageUploadTests(TestCase):
    pass