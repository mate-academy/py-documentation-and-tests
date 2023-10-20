from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from rest_framework.test import APIClient

from cinema.models import Movie, Actor, Genre
from cinema.serializers import MovieSerializer, MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")

def detail_url(movie_id: int):
    return reverse("cinema:movie-detail", args=[movie_id])


def sample_movie(**params):
    defaults = {
        "title": "Sample Movie",
        "description": "Sample description",
        "duration": 150,
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
            "testpass",
        )
        self.client.force_authenticate(self.user)

    def test_list_movies(self):
        sample_movie()
        movie_with_genres = sample_movie()

        genre1 = sample_genre()
        genre2 = sample_genre(name="Thriller")

        movie_with_genres.genres.add(genre1, genre2)

        res = self.client.get(MOVIE_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movie_by_genre(self):
        movie1 = sample_movie()
        movie2 = sample_movie()

        genre1 = sample_genre()
        genre2 = sample_genre(name="Thriller")

        movie1.genres.add(genre1)
        movie2.genres.add(genre2)

        movie_without_genre = sample_movie()

        res = self.client.get(MOVIE_URL, {"genres": f"{genre1.id},{genre2.id}"})

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie_without_genre)

        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_filter_movie_by_actor(self):
        movie1 = sample_movie()
        movie2 = sample_movie()

        actor1 = sample_actor()
        actor2 = sample_actor()

        movie1.actors.add(actor1)
        movie2.actors.add(actor2)

        movie_without_actor = sample_movie()

        res = self.client.get(MOVIE_URL, {"actors": f"{actor1.id},{actor2.id}"})

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie_without_actor)

        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        movie.genres.add(Genre.objects.create(name="Comedy"))

        url = detail_url(movie.id)
        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        genre = sample_genre()
        actor = sample_actor()

        payload = {
            "title": "test title",
            "description": "test description",
            "duration": 120,
            "genre": genre.id,
            "actor": actor.id
        }

        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@admin.com",
            "testpass",
            is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        genre = sample_genre()
        actor = sample_actor()

        payload = {
            "title": "test title",
            "description": "test description",
            "duration": 120,
            "genres": genre.id,
            "actors": actor.id
        }

        res = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=res.data["id"])
        genres = movie.genres.all()
        actors = movie.actors.all()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        self.assertEqual(actors.count(), 1)
        self.assertEqual(genres.count(), 1)
        self.assertIn(genre, genres)
        self.assertIn(actor, actors)

    def test_delete_movie_not_allowed(self):
        movie = sample_movie()
        url = detail_url(movie.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
