from unittest import TestCase

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status

from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")


def detail_url(movie_id: int):
    return reverse("cinema:movie-detail", args=[movie_id])


def sample_movie(**params):
    defaults = {
        "title": "Movie",
        "description": "Description",
        "duration": 100,
    }
    defaults.update(params)

    return Movie.objects.create(**defaults)


class UnauthenticatedMovieApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user, _ = get_user_model().objects.get_or_create(
            email="test@email.com",
            defaults={"password": "password"}
        )
        self.client.force_authenticate(self.user)

        self.genre, _ = Genre.objects.get_or_create(name="novel")

    def test_list_movies(self):
        sample_movie()
        movie_with_genre = sample_movie()
        movie_with_actor = sample_movie()

        actor = Actor.objects.create(first_name="Ada", last_name="Maas")

        movie_with_genre.genres.add(self.genre)
        movie_with_actor.actors.add(actor)

        res = self.client.get(MOVIE_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_genres_and_actors(self):
        movie1 = sample_movie(title="Movie 1")

        actor1 = Actor.objects.create(first_name="name", last_name="test")

        movie1.genres.add(self.genre)
        movie1.actors.add(actor1)

        movie3 = sample_movie(title="Movie without genres")

        res = self.client.get(MOVIE_URL, {"genres": f"{self.genre.id}", "actors": f"{actor1.id}"})

        serializer1 = MovieListSerializer(movie1)
        serializer3 = MovieListSerializer(movie3)

        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        movie.genres.add(self.genre)
        movie.actors.add(Actor.objects.create(first_name="Nick", last_name="Black"))

        url = detail_url(movie.id)
        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Movie",
            "description": "test",
            "duration": 120,
        }

        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@addmin.com",
            "testpassword",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)

        self.genre, _ = Genre.objects.get_or_create(name="novel")
        self.actor = Actor.objects.create(first_name="John", last_name="Dg")

    def test_movie_created(self):
        payload = {
            "title": "Movie",
            "description": "test",
            "duration": 120,
            "genres": self.genre.id,
            "actors": [self.actor.id]
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
