from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import Genre, Actor, Movie
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")


def detail_url(movie_id: int):
    return reverse("cinema:movie-detail", args=[movie_id])


def sample_genre(**param) -> Genre:
    defaults = {
        "name": "Sci-Fi"
    }
    defaults.update(param)

    return Genre.objects.create(**defaults)


def sample_actor(**param) -> Actor:
    defaults = {
        "first_name": "Robert",
        "last_name": "Downey",
    }
    defaults.update(param)

    return Actor.objects.create(**defaults)


def sample_movie(**params) -> Movie:
    defaults = {
        "title": "Dune",
        "description": "Best movie",
        "duration": 150,
    }
    defaults.update(params)

    return Movie.objects.create(**defaults)


class UnAuthenticatedMovieViesSet(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self) -> None:
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieViewSet(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "rob.down@movie.com",
            "Matrix12345",
        )

        self.movie1 = sample_movie(title="movie_1")
        self.movie2 = sample_movie(title="movie_2")
        self.movie3 = sample_movie()

        self.genre1 = sample_genre(name="genre_1")
        self.genre2 = sample_genre(name="genre_2")

        self.actor1 = sample_actor(first_name="first_1", last_name="last_1")
        self.actor2 = sample_actor(first_name="first_2", last_name="last_2")

        self.client.force_authenticate(self.user)

    def test_list_movies(self):
        sample_movie()

        movie_with_genre = sample_movie()
        movie_with_genre.genres.add(self.genre1, self.genre2)

        movie_with_actor = sample_movie()
        movie_with_actor.actors.add(self.actor1, self.actor2)

        result = self.client.get(MOVIE_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(result.status_code, status.HTTP_200_OK)
        self.assertEqual(result.data, serializer.data)

    def test_movie_filter_by_title(self):
        result = self.client.get(MOVIE_URL, {"title": "movie"})

        serializer1 = MovieListSerializer(self.movie1)
        serializer2 = MovieListSerializer(self.movie2)
        serializer3 = MovieListSerializer(self.movie3)

        self.assertIn(serializer1.data, result.data)
        self.assertIn(serializer2.data, result.data)
        self.assertNotIn(serializer3.data, result.data)

    def movie_filter_by_genre(self):
        movie_with_genre1 = self.movie1.genres.add(self.genre1)
        movie_with_genre2 = self.movie2.genres.add(self.genre2)
        movie_without_genre = self.movie3

        result = self.client.get(
            MOVIE_URL,
            {"genres": f"{self.genre1.id},{self.genre2.id}"}
        )

        serializer1 = MovieListSerializer(movie_with_genre1)
        serializer2 = MovieListSerializer(movie_with_genre2)
        serializer3 = MovieListSerializer(movie_without_genre)

        self.assertIn(serializer1.data, result.data)
        self.assertIn(serializer2.data, result.data)
        self.assertNotIn(serializer3.data, result.data)

    def movi_filter_by_actor(self):
        movie_with_actor1 = self.movie1.actors.add(self.actor1)
        movie_with_actor2 = self.movie1.actors.add(self.actor2)
        movie_without_actor = self.movie3

        result = self.client.get(
            MOVIE_URL,
            {"actors": f"{self.actor1.id},{self.actor2.id}"}
        )

        serializer1 = MovieListSerializer(movie_with_actor1)
        serializer2 = MovieListSerializer(movie_with_actor2)
        serializer3 = MovieListSerializer(movie_without_actor)

        self.assertIn(serializer1.data, result.data)
        self.assertIn(serializer2.data, result.data)
        self.assertNotIn(serializer3.data, result.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        movie.genres.add(sample_genre())

        url = detail_url(movie.id)
        result = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(result.status_code, status.HTTP_200_OK)
        self. assertEqual(result.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "title",
            "description": "description",
            "duration": 100,
        }

        result = self.client.post(MOVIE_URL, payload)
        self.assertEqual(result.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@admin.com",
            "Password12345",
            is_staff=True,
        )

        self.movie1 = sample_movie(title="movie_1")
        self.genre1 = sample_genre(name="genre_1")
        self.actor1 = sample_actor(first_name="first_1", last_name="last_1")

        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        payload = {
            "title": "movie",
            "description": "best movie",
            "duration": 200,
            "genres": self.genre1.id,
            "actors": self.actor1.id,
        }

        result = self.client.post(MOVIE_URL, payload)

        self.assertEqual(result.status_code, status.HTTP_201_CREATED)

    def test_delete_movie_not_allowed(self):
        movie = self.movie1

        url = detail_url(movie.id)

        result = self.client.delete(url)

        self.assertEqual(result.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)