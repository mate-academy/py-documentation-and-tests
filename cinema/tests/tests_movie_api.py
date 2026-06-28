import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from cinema.serializers import (
    MovieSerializer,
    MovieListSerializer,
    MovieDetailSerializer,
)

MOVIE_URL = reverse("cinema:movie-list")


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=(movie_id,))


def sample_movie(**params) -> Movie:
    defaults = {
        "title": "Movie Title",
        "description": "Movie Description",
        "duration": 60,
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)


class UnauthenticatedMovieAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.test",
            password="test_password",
        )
        self.client.force_authenticate(self.user)

    def test_movies_list(self):
        sample_movie()

        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_title(self):
        sample_movie()
        movie_with_another_title = sample_movie(title="Test Title")

        res = self.client.get(MOVIE_URL, {"title": "Test Title"})
        serializer = MovieListSerializer([movie_with_another_title], many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(serializer.data, res.data)

    def test_filter_movies_by_genres(self):
        movie_without_genre = sample_movie()
        movie_with_genre_1 = sample_movie()
        movie_with_genre_2 = sample_movie()

        genre_1 = Genre.objects.create(name="Genre1")
        genre_2 = Genre.objects.create(name="Genre2")

        movie_with_genre_1.genres.add(genre_1)
        movie_with_genre_2.genres.add(genre_2)

        res = self.client.get(MOVIE_URL, {"genres": f"{genre_1.id},{genre_2.id}"})
        serializer = MovieListSerializer([movie_without_genre], many=True)
        serializer_movie_genres_1 = MovieListSerializer([movie_with_genre_1], many=True)
        serializer_movie_genres_2 = MovieListSerializer([movie_with_genre_2], many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertNotIn(serializer.data, res.data)
        self.assertIn(serializer_movie_genres_1.data[0], res.data)
        self.assertIn(serializer_movie_genres_2.data[0], res.data)

    def test_filter_movies_by_actors(self):
        movie_without_actor = sample_movie()
        movie_with_actor_1 = sample_movie()
        movie_with_actor_2 = sample_movie()

        actor_1 = Actor.objects.create(first_name="Actor1", last_name="Test")
        actor_2 = Actor.objects.create(first_name="Actor2", last_name="Test")

        movie_with_actor_1.actors.add(actor_1)
        movie_with_actor_2.actors.add(actor_2)

        res = self.client.get(MOVIE_URL, {"actors": f"{actor_1.id},{actor_2.id}"})
        serializer = MovieListSerializer([movie_without_actor], many=True)
        serializer_movie_actors_1 = MovieListSerializer([movie_with_actor_1], many=True)
        serializer_movie_actors_2 = MovieListSerializer([movie_with_actor_2], many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertNotIn(serializer.data, res.data)
        self.assertIn(serializer_movie_actors_1.data[0], res.data)
        self.assertIn(serializer_movie_actors_2.data[0], res.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        url = detail_url(movie.id)
        res = self.client.get(url)
        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Movie Title",
            "description": "Movie Description",
            "duration": 60,
        }

        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@admin.admin",
            password="test_password",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        genre = Genre.objects.create(name="Action")
        actor = Actor.objects.create(first_name="John", last_name="Doe")
        payload = {
            "title": "Movie Title",
            "description": "Movie Description",
            "duration": 60,
            "genres": [genre.id],
            "actors": [actor.id],
        }

        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(id=res.data["id"])

        for key in payload:
            if key in ["genres", "actors"]:
                movie_values = list(getattr(movie, key).values_list("id", flat=True))
                self.assertEqual(payload[key], movie_values)
            else:
                self.assertEqual(payload[key], getattr(movie, key))
