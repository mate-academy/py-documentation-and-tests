from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieSerializer, MovieDetailSerializer
from cinema.tests.test_movie_api import sample_movie, detail_url

MOVIE_URL = reverse("cinema:movie-list")


class UnauthenticatedMovieApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_requires(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@test.com",
            "testpass",
        )
        self.client.force_authenticate(self.user)

    def test_list_movies(self):
        sample_movie()
        movie_with_genre = sample_movie()
        movie_with_actors = sample_movie()

        genre = Genre.objects.create(name="TestGenre1")
        actor = Actor.objects.create(first_name="Actor", last_name="Test")

        movie_with_genre.genres.add(genre)
        movie_with_actors.actors.add(actor)

        res = self.client.get(MOVIE_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_genre(self):
        movie1 = sample_movie(title="movie1")
        movie2 = sample_movie(title="movie2")

        genre1 = Genre.objects.create(name="Genre1")
        genre2 = Genre.objects.create(name="Genre2")

        movie1.genres.add(genre1)
        movie2.genres.add(genre2)

        movie3 = sample_movie(title="Movie without genre")

        res = self.client.get(
            MOVIE_URL, {"genres": f"{genre1.id},{genre2.id}"}
        )

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie3)

        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_filter_movies_by_actor(self):
        movie1 = sample_movie(title="movie1")
        movie2 = sample_movie(title="movie2")

        actor1 = Actor.objects.create(first_name="Actor1", last_name="Test1")
        actor2 = Actor.objects.create(first_name="Actor2", last_name="Test2")

        movie1.actors.add(actor1)
        movie2.actors.add(actor2)

        movie3 = sample_movie(title="Movie without actor")

        res = self.client.get(
            MOVIE_URL, {"actors": f"{actor1.id},{actor2.id}"}
        )

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie3)

        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_filter_movies_by_title(self):
        movie1 = sample_movie(title="movie1")
        movie2 = sample_movie(title="movie2")

        res = self.client.get(
            MOVIE_URL, {"title": f"{movie1.title}"}
        )

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)

        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        movie.genres.add(Genre.objects.create(name="TestGenre"))
        movie.actors.add(
            Actor.objects.create(first_name="Actor", last_name="Test")
        )

        url = detail_url(movie.id)
        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Test movie",
            "description": "Movie description",
            "duration": 120,
        }

        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@test.com",
            "testpass",
            is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        payload = {
            "title": "Test movie",
            "description": "Movie description",
            "duration": 120,
        }

        res = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_create_movie_with_genres_and_actors(self):
        genre1 = Genre.objects.create(name="Genre1")
        genre2 = Genre.objects.create(name="Genre2")

        actor1 = Actor.objects.create(first_name="Actor1", last_name="Test1")
        actor2 = Actor.objects.create(first_name="Actor2", last_name="Test2")

        payload = {
            "title": "Test movie",
            "description": "Movie description",
            "duration": 120,
            "genres": [genre1.id, genre2.id],
            "actors": [actor1.id, actor2.id],
        }

        res = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(id=res.data["id"])
        genres = movie.genres.all()
        actors = movie.actors.all()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(genres.count(), 2)
        self.assertIn(genre1, genres)
        self.assertIn(genre2, genres)

        self.assertEqual(actors.count(), 2)
        self.assertIn(actor1, actors)
        self.assertIn(actor2, actors)

    def test_delete_and_put_movie_not_allowed(self):
        movie = sample_movie()
        url = detail_url(movie.id)

        res_del = self.client.delete(url)
        res_put = self.client.put(url)

        self.assertEqual(res_del.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(res_put.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


