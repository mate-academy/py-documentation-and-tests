from django.contrib.auth import get_user_model
from django.test import TestCase
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
        "title": "Batman",
        "duration": 60,
        "description": "test description",
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)


def sample_genre(**params):
    defaults = {
        "name": "Drama",
    }
    defaults.update(params)

    return Genre.objects.create(**defaults)


def sample_actor(**params):
    defaults = {"first_name": "George", "last_name": "Clooney"}
    defaults.update(params)

    return Actor.objects.create(**defaults)


class UnauthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(MOVIE_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticationMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@test.com",
            "test1234",
        )
        self.client.force_authenticate(self.user)

    def test_list_movies(self):
        sample_movie()
        movie_with_actor = sample_movie()
        movie_with_genre = sample_movie()

        actor = sample_actor()
        genre = sample_genre()

        movie_with_actor.actors.add(actor)
        movie_with_genre.genres.add(genre)

        response = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_filter_movie_by_title(self):
        movie1 = sample_movie(title="batman")
        movie2 = sample_movie(title="vatman")

        response = self.client.get(MOVIE_URL, {"title": movie1})
        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)

        self.assertIn(serializer1.data, response.data)
        self.assertNotIn(serializer2.data, response.data)

    def test_filter_movie_by_genre(self):
        movie1 = sample_movie(title="batman")
        movie2 = sample_movie(title="vatman")

        genre1 = sample_genre(name="action")
        genre2 = sample_genre(name="drama")

        movie1.genres.add(genre1)
        movie2.genres.add(genre2)
        movie3 = sample_movie(title="Movie without genre")

        response = self.client.get(
            MOVIE_URL, {"genres": f"{genre1.id},{genre2.id}"}
        )

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie3)

        self.assertIn(serializer1.data, response.data)
        self.assertIn(serializer2.data, response.data)
        self.assertNotIn(serializer3.data, response.data)

    def test_filter_movie_by_actor(self):
        movie1 = sample_movie(title="batman")
        movie2 = sample_movie(title="vatman")

        actor1 = sample_actor(first_name="Bob", last_name="Dylan")
        actor2 = sample_actor(first_name="Zak", last_name="Wobler")

        movie1.actors.add(actor1)
        movie2.actors.add(actor2)
        movie3 = sample_movie(title="Movie without actor")

        response = self.client.get(
            MOVIE_URL, {"actors": f"{actor1.id},{actor2.id}"}
        )

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie3)

        self.assertIn(serializer1.data, response.data)
        self.assertIn(serializer2.data, response.data)
        self.assertNotIn(serializer3.data, response.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()

        url = detail_url(movie.id)
        response = self.client.get(url)
        serializer = MovieDetailSerializer(movie)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Tesman",
            "duration": 20
        }
        response = self.client.post(MOVIE_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@test.com",
            "test12345",
            is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_movie_by_admin_with_genres_and_actors(self):
        genre = sample_genre(name="Drama")
        actor = sample_actor(first_name="Luis", last_name="Armstrong")
        payload = {
            "title": "Tesman",
            "description": "Test description",
            "duration": 100,
            "actors": [actor.id],
            "genres": [genre.id]
        }
        response = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=response.data["id"])
        actors = movie.actors.all()
        genres = movie.genres.all()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_doesnt_create_movie_by_admin_without_genres_and_actors(self):
        payload = {
            "title": "Tesman",
            "duration": 20
        }
        response = self.client.post(MOVIE_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_movie_not_allowed(self):
        movie = sample_movie()
        url = detail_url(movie.id)

        response = self.client.delete(url)

        self.assertEqual(
            response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )
