from django.contrib.auth import get_user_model
from django.contrib.sites import requests
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from cinema.models import Movie, Actor, Genre
from cinema.serializers import MovieSerializer, MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


def sample_movie(**params) -> Movie:
    defaults = {
        "title": "test",
        "description": "test",
        "duration": 12,
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
            password="testpassword",
        )
        self.client.force_authenticate(user=self.user)

    def test_movie_list(self):
        sample_movie()

        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_title(self):
        movie_1 = sample_movie()
        movie_2 = sample_movie(title="wow")

        res = self.client.get(
            MOVIE_URL,
            {"title": movie_2.title},
        )

        movie_1_serializer = MovieListSerializer(movie_1)
        movie_2_serializer = MovieListSerializer(movie_2)

        self.assertIn(movie_2_serializer.data, res.data)
        self.assertNotIn(movie_1_serializer.data, res.data)

    def test_filter_movies_by_actors(self):
        movie_1 = sample_movie()
        movie_2 = sample_movie(title="wow")

        actor_1 = Actor.objects.create(
            first_name="Test",
            last_name="Test",
        )
        actor_2 = Actor.objects.create(
            first_name="Testy",
            last_name="Testy",
        )

        movie_1.actors.add(actor_1)
        movie_2.actors.add(actor_2)

        res = self.client.get(
            MOVIE_URL,
            {"actors": actor_1.id}
        )

        movie_1_serializer = MovieListSerializer(movie_1)
        movie_2_serializer = MovieListSerializer(movie_2)

        self.assertIn(movie_1_serializer.data, res.data)
        self.assertNotIn(movie_2_serializer.data, res.data)

    def test_filter_movies_by_genres(self):
        movie_1 = sample_movie()
        movie_2 = sample_movie(title="wow")

        genre_1 = Genre.objects.create(name="Drama")
        genre_2 = Genre.objects.create(name="Sci-Fi")

        movie_1.genres.add(genre_1)
        movie_2.genres.add(genre_2)

        res = self.client.get(
            MOVIE_URL,
            {"genres": genre_2.id},
        )

        movie_1_serializer = MovieListSerializer(movie_1)
        movie_2_serializer = MovieListSerializer(movie_2)

        self.assertIn(movie_2_serializer.data, res.data)
        self.assertNotIn(movie_1_serializer.data, res.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        genre = Genre.objects.create(name="Drama")
        actor = Actor.objects.create(
            first_name="Test",
            last_name="Test",
        )
        movie.genres.add(genre)
        movie.actors.add(actor)

        url = detail_url(movie.id)

        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "test",
            "description": "test",
            "duration": 12
        }

        res = self.client.post(
            MOVIE_URL,
            payload
        )

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com",
            password="testpassword",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.user)

    def test_create_movie(self):
        payload = {
            "title": "test",
            "description": "test",
            "duration": 12
        }

        res = self.client.post(
            MOVIE_URL,
            payload
        )

        movie = Movie.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_create_movie_with_actors(self):
        actor_1 = Actor.objects.create(
            first_name="Test",
            last_name="Test",
        )
        actor_2 = Actor.objects.create(
            first_name="Testy",
            last_name="Testy",
        )
        payload = {
            "title": "test",
            "description": "test",
            "duration": 12,
            "actors": [actor_1.id, actor_2.id]
        }

        res = self.client.post(
            MOVIE_URL,
            payload
        )

        movie = Movie.objects.get(id=res.data["id"])
        actors = movie.actors.all()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn(actor_1, actors)
        self.assertIn(actor_2, actors)
        self.assertEqual(actors.count(), 2)

    def test_create_movie_with_genres(self):
        genre_1 = Genre.objects.create(name="Drama")
        genre_2 = Genre.objects.create(name="Sci-Fi")

        payload = {
            "title": "test",
            "description": "test",
            "duration": 12,
            "genres": [genre_1.id, genre_2.id]
        }

        res = self.client.post(
            MOVIE_URL,
            payload
        )

        movie = Movie.objects.get(id=res.data["id"])
        genres = movie.genres.all()
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn(genre_1, genres)
        self.assertIn(genre_2, genres)
        self.assertEqual(genres.count(), 2)
