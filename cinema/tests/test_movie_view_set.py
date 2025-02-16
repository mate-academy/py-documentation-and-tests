from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from cinema.serializers import (
    MovieListSerializer,
    MovieDetailSerializer,
)

MOVIE_URL = reverse("cinema:movie-list")


class UnauthenticatedMovieAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(MOVIE_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


def sample_movie(**params) -> Movie:
    defaults = {
        "title": "Sample Movie Title",
        "description": "Sample Movie Description",
        "duration": 60,
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)


def detail_url(movie_id):
    return reverse(
        "cinema:movie-detail",
        args=[
            movie_id,
        ],
    )


class AuthenticatedMovieAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.test",
            password="testpassword",
        )
        self.client.force_authenticate(self.user)

    def test_movies_list(self):
        sample_movie()
        movie_with_genres_and_actors = sample_movie()

        genre_1 = Genre.objects.create(name="Test1")
        genre_2 = Genre.objects.create(name="Test2")

        actor_1 = Actor.objects.create(
            first_name="Test1",
            last_name="Test1",
        )
        actor_2 = Actor.objects.create(
            first_name="Test2",
            last_name="Test2",
        )

        movie_with_genres_and_actors.genres.add(genre_1, genre_2)
        movie_with_genres_and_actors.actors.add(actor_1, actor_2)

        response = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_filter_movies_by_titles(self):
        movie_1 = sample_movie(title="My new movie")
        movie_2 = sample_movie(title="Test")

        response = self.client.get(
            MOVIE_URL,
            {"title": f"{movie_1.title}"},
        )

        serializer_movie_1 = MovieListSerializer(movie_1)
        serializer_movie_2 = MovieListSerializer(movie_2)

        self.assertIn(serializer_movie_1.data, response.data)
        self.assertNotIn(serializer_movie_2.data, response.data)

    def test_filter_movies_by_genres(self):
        movie_without_genres = sample_movie()
        movie_with_genre_1 = sample_movie(title="Movie1")
        movie_with_genre_2 = sample_movie(title="Movie2")

        genre_1 = Genre.objects.create(name="Test1")
        genre_2 = Genre.objects.create(name="Test2")

        movie_with_genre_1.genres.add(genre_1)
        movie_with_genre_2.genres.add(genre_2)

        response = self.client.get(
            MOVIE_URL,
            {"genres": f"{genre_1.id},{genre_2.id}"},
        )

        serializer_without_genres = MovieListSerializer(movie_without_genres)
        serializer_movie_genres_1 = MovieListSerializer(movie_with_genre_1)
        serializer_movie_genres_2 = MovieListSerializer(movie_with_genre_2)

        self.assertIn(serializer_movie_genres_1.data, response.data)
        self.assertIn(serializer_movie_genres_2.data, response.data)
        self.assertNotIn(serializer_without_genres.data, response.data)

    def test_filter_movies_by_actors(self):
        movie_without_actors = sample_movie()
        movie_with_actors_1 = sample_movie(title="Movie1")
        movie_with_actors_2 = sample_movie(title="Movie2")

        actor_1 = Actor.objects.create(
            first_name="Test1",
            last_name="Test1",
        )
        actor_2 = Actor.objects.create(
            first_name="Test2",
            last_name="Test2",
        )

        movie_with_actors_1.actors.add(actor_1)
        movie_with_actors_2.actors.add(actor_2)

        response = self.client.get(
            MOVIE_URL,
            {"actors": f"{actor_1.id},{actor_2.id}"},
        )

        serializer_without_actors = MovieListSerializer(movie_without_actors)
        serializer_movie_actors_1 = MovieListSerializer(movie_with_actors_1)
        serializer_movie_actors_2 = MovieListSerializer(movie_with_actors_2)

        self.assertIn(serializer_movie_actors_1.data, response.data)
        self.assertIn(serializer_movie_actors_2.data, response.data)
        self.assertNotIn(serializer_without_actors.data, response.data)

    def test_retrieve_movie_by_id(self):
        movie = sample_movie()

        genre = Genre.objects.create(name="Test1")
        actor = Actor.objects.create(first_name="Test1", last_name="Test2")

        movie.genres.add(genre)
        movie.actors.add(actor)

        url = detail_url(movie.id)

        response = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "My new movie",
            "description": "My new movie",
            "duration": 60,
        }
        response = self.client.post(MOVIE_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@admin.test",
            password="testpassword",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        payload = {
            "title": "My new movie",
            "description": "My new movie",
            "duration": 60,
        }
        response = self.client.post(MOVIE_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        movie = Movie.objects.get(id=response.data["id"])

        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_create_movie_with_actors_and_genres(self):
        genre_1 = Genre.objects.create(name="Test1")
        actor_1 = Actor.objects.create(first_name="Test1", last_name="Test2")

        payload = {
            "title": "My new movie",
            "description": "My new movie",
            "duration": 60,
            "actors": [actor_1.id],
            "genres": [genre_1.id],
        }

        response = self.client.post(MOVIE_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        movie = Movie.objects.get(id=response.data["id"])
        actors = movie.actors.all()
        genres = movie.genres.all()

        self.assertIn(actor_1, actors)
        self.assertIn(genre_1, genres)

        self.assertEqual(actors.count(), 1)
        self.assertEqual(genres.count(), 1)
