from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import Genre, Movie, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")


def sample_movie(**params):
    defaults = {
        "title": "Test",
        "description": "Test description",
        "duration": 90
    }

    defaults.update(params)

    return Movie.objects.create(**defaults)


def sample_genre(**params):
    default = {
        "name": "Test genre"
    }
    default.update(params)

    return Genre.objects.create(**default)


def sample_actor(**params):
    default = {
        "first_name": "Test name",
        "last_name": "Test surname"
    }
    default.update(params)

    return Actor.objects.create(**default)


def detail_url(movie_id: int):
    return reverse("cinema:movie-detail", args=[movie_id])


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
            "test@test.com",
            "test12345"
        )
        self.client.force_authenticate(self.user)

    def test_list_movie(self):
        sample_movie(title="Movie 1")
        movie_with_genre = sample_movie(title="Movie 2")
        movie_with_actor = sample_movie(title="Movie 3")

        genre = sample_genre()
        actor = sample_actor()

        movie_with_genre.genres.add(genre)
        movie_with_actor.actors.add(actor)

        res = self.client.get(MOVIE_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.data, serializer.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_filter_movie_by_title(self):
        movie1 = sample_movie(title="Movie 1")
        movie2 = sample_movie(title="Movie 2")
        movie3 = sample_movie(title="Movie 3")

        actor = sample_actor()
        genre = sample_genre()

        movie1.actors.add(actor)
        movie2.genres.add(genre)

        res1 = self.client.get(MOVIE_URL, {"actors": f"{actor.id}"})
        res2 = self.client.get(MOVIE_URL, {"genres": f"{genre.id}"})
        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie3)

        self.assertIn(serializer1.data, res1.data)
        self.assertIn(serializer2.data, res2.data)
        self.assertNotIn(serializer3.data, res1.data)
        self.assertNotIn(serializer3.data, res2.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        movie.genres.add(sample_genre())

        url = detail_url(movie.id)
        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.data, serializer.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Movie",
            "description": "Movie description",
            "duration": 90
        }

        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@admin.com",
            "admin12345",
            is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        payload = {
            "title": "Movie",
            "description": "Movie description",
            "duration": 90
        }

        res = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_create_movie_with_actor_genre(self):
        actor = sample_actor()
        genre = sample_genre()

        payload = {
            "title": "Movie",
            "description": "Movie description",
            "duration": 90,
            "actors": [actor.id],
            "genres": [genre.id]
        }

        res = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=res.data["id"])

        actors = movie.actors.all()
        genres = movie.genres.all()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(actors.count(), 1)
        self.assertEqual(genres.count(), 1)
        self.assertIn(actor, actors)
        self.assertIn(genre, genres)

    def test_delete_movie_forbidden(self):
        movie = sample_movie()

        url = detail_url(movie.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
