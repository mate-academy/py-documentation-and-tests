from unittest import TestCase

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status

from cinema.models import Movie
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

from rest_framework.test import APIClient

from cinema.tests.test_movie_api import sample_movie, sample_actor, sample_genre, detail_url

MOVIE_URL = reverse("cinema:movie-list")
MOVIE_SESSION_URL = reverse("cinema:moviesession-list")


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
            "test_auth@test.com",
            "test_auth_password"
        )
        self.client.force_authenticate(self.user)

    def test_list_movies(self):
        sample_movie()
        movie_with_actors_and_genre = sample_movie()

        actor = sample_actor()
        genre = sample_genre()

        movie_with_actors_and_genre.actors.add(actor)
        movie_with_actors_and_genre.genres.add(genre)

        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filtering_by_title(self):
        movie1 = sample_movie(title="movie1")
        movie2 = sample_movie(title="movie2")

        res = self.client.get(MOVIE_URL, {"title": f"{movie1.title}"})

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

    def test_filtering_by_genres(self):
        movie1 = sample_movie(title="movie1")
        movie2 = sample_movie(title="movie2")
        movie3 = sample_movie()

        genre1 = sample_genre(name="drama")
        genre2 = sample_genre(name="horror")

        movie1.genres.add(genre1)
        movie2.genres.add(genre2)

        res = self.client.get(MOVIE_URL, {"genres": f"{genre1.id},{genre2.id}"})

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie3)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_filtering_by_actors(self):
        movie1 = sample_movie(title="movie1")
        movie2 = sample_movie(title="movie2")
        movie3 = sample_movie()

        actor1 = sample_actor(first_name="John", last_name="Doe")
        actor2 = sample_actor(first_name="Harry", last_name="HarryPotter")

        movie1.actors.add(actor1)
        movie2.actors.add(actor2)

        res = self.client.get(MOVIE_URL, {"actors": f"{actor1.id},{actor2.id}"})

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie3)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        movie.actors.add(sample_actor())
        movie.genres.add(sample_genre())

        url = detail_url(movie.id)
        res = self.client.get(url)
        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Title",
            "description": "Description",
            "duration": "Duration",
            "actors": [sample_actor().id],
            "genres": [sample_genre().id]
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@admin.com",
            "password",
            is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        payload = {
            "title": "Title",
            "description": "Description",
            "duration": 90,
            "actors": [sample_actor().id],
            "genres": [sample_genre().id]
        }
        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_create_movie_without_actors_and_genre(self):
        payload = {
            "title": "Title",
            "description": "Description",
            "duration": 90
        }
        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
