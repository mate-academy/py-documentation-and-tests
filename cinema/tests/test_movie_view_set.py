from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.test import TestCase

from cinema.models import Movie, Actor, Genre
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")


def sample_movie(**params):
    defaults = {
        "title": "Test title",
        "description": "Test description",
        "duration": 10,
    }
    defaults.update(params)

    return Movie.objects.create(**defaults)


def detail_url(movie_id:int):
    return reverse("cinema:movie-detail", args=[movie_id])


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
            "test@test.com",
            "test12345",
        )
        self.client.force_authenticate(self.user)

    def test_list_movies(self):
        sample_movie()
        movie_with_actor_and_genre = sample_movie()

        actor = Actor.objects.create(first_name="Test", last_name="Testich")
        genre = Genre.objects.create(name="Drama")

        movie_with_actor_and_genre.actors.add(actor)
        movie_with_actor_and_genre.genres.add(genre)

        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movie_by_title(self):
        movie1 = sample_movie(title="Movie 1")
        movie2 = sample_movie(title="Movie 2")

        res = self.client.get(MOVIE_URL, {"title": movie1.title})

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)

        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

    def test_filter_movie_by_actor(self):
        movie1 = sample_movie(title="Movie 1")
        movie2 = sample_movie(title="Movie 2")

        actor = Actor.objects.create(first_name="Test", last_name="Testich")

        movie1.actors.add(actor)

        res = self.client.get(MOVIE_URL, {"actors": actor.id})

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)

        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

    def test_filter_movie_by_genre(self):
        movie1 = sample_movie(title="Movie 1")
        movie2 = sample_movie(title="Movie 2")

        genre = Genre.objects.create(name="Drama")

        movie1.genres.add(genre)

        res = self.client.get(MOVIE_URL, {"genres": genre.id})

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)

        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()

        actor = Actor.objects.create(first_name="Test", last_name="Testich")
        genre = Genre.objects.create(name="Drama")

        movie.actors.add(actor)
        movie.genres.add(genre)

        url = detail_url(movie.id)
        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Test title",
            "description": "Test description",
            "duration": 10,
        }

        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

        self.user = get_user_model().objects.create_user(
            "admin@admin.com",
            "test12345",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        payload = {
            "title": "Test title",
            "description": "Test description",
            "duration": 10,
        }

        res = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_create_movie_with_actor_and_genre(self):
        actor = Actor.objects.create(first_name="Test", last_name="Testich")
        genre = Genre.objects.create(name="Drama")

        payload = {
            "title": "Test title",
            "description": "Test description",
            "duration": 10,
            "actors": actor.id,
            "genres": genre.id
        }

        res = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=res.data["id"])
        actors = movie.actors.all()
        genres = movie.genres.all()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn(actor, actors)
        self.assertIn(genre, genres)

    def test_delete_movie_denied(self):
        movie = sample_movie()

        url = detail_url(movie.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
