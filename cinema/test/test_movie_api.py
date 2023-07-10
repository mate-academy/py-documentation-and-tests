from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import Movie, Actor, Genre
from cinema.serializers import (
    MovieListSerializer,
    MovieDetailSerializer
)

MOVIE_URL = reverse("cinema:movie-list")


def detail_url(movie_id: int):
    return reverse("cinema:movie-detail", args=[movie_id])


def sample_movie(**params):
    default = {
        "title": "Sample movie",
        "duration": 120,
    }
    default.update(params)

    return Movie.objects.create(**default)


class UnauthenticatedMovieApiTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@gmail.com",
            "testpassword"
        )
        self.client.force_authenticate(self.user)

    def test_list_movies(self):
        sample_movie()
        movie_with_genres = sample_movie()

        genre1 = Genre.objects.create(name="Drama")
        genre2 = Genre.objects.create(name="Action")

        movie_with_genres.genres.add(genre1, genre2)

        res = self.client.get(MOVIE_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_genres(self):
        movie1 = sample_movie(title="Movie 1")
        movie2 = sample_movie(title="Movie 2")

        genre1 = Genre.objects.create(name="Drama")
        genre2 = Genre.objects.create(name="Action")

        movie1.genres.add(genre1)
        movie2.genres.add(genre2)

        res = self.client.get(MOVIE_URL, {
            "genres": f"{genre1.id},"
                      f"{genre2.id}"
        })

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)

        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        movie.genres.add(Genre.objects.create(name="Drama"))

        url = detail_url(movie.id)
        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Movie",
            "duration": 120,
        }

        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@admin.com",
            "testpassword",
            is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        genre1 = Genre.objects.create(name="Drama")
        genre2 = Genre.objects.create(name="Action")

        actor1 = Actor.objects.create(first_name="Matt", last_name="Damon")
        actor2 = Actor.objects.create(first_name="Elliot", last_name="Page")

        payload = {
            "title": "Movie",
            "description": "Sample description",
            "duration": 100,
            "genres": [genre1.id, genre2.id],
            "actors": [actor1.id, actor2.id],
        }

        res = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=res.json()["id"])
        genres = movie.genres.all()
        actors = movie.actors.all()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(genres.count(), 2)
        self.assertEqual(actors.count(), 2)
        self.assertIn(genre1, genres)
        self.assertIn(genre2, genres)
        self.assertIn(actor1, actors)
        self.assertIn(actor2, actors)

    def test_delete_movie_not_allowed(self):
        movie = sample_movie()
        url = detail_url(movie.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
