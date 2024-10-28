from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=(movie_id,))


def sample_movie(**params) -> Movie:

    defaults = {
        "title": "title1",
        "description": "some description",
        "duration": 90,
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)


def sample_actor(**params) -> Actor:
    defaults = {
        "first_name": "John",
        "last_name": "Smith",
    }
    defaults.update(params)
    return Actor.objects.create(**defaults)


def sample_genre(**params) -> Genre:
    defaults = {"name": "drama"}
    defaults.update(params)
    return Genre.objects.create(**defaults)


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
            email="test@test.test",
            password="testpassword"
        )
        self.client.force_authenticate(self.user)

    def test_movies_list(self):
        sample_movie()
        movie_with_actor_and_genre = sample_movie()
        genre_1 = sample_genre()
        genre_2 = sample_genre(name="comedy")
        actor_1 = sample_actor()
        actor_2 = sample_actor(
            first_name="James",
            last_name="Potter"
        )
        movie_with_actor_and_genre.actors.add(actor_1, actor_2)
        movie_with_actor_and_genre.genres.add(genre_1, genre_2)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_by_title(self):
        movie_1 = sample_movie()
        movie_2 = sample_movie(title="title2")

        res = self.client.get(
            MOVIE_URL,
            {"title": f"{movie_2.title}"}
        )
        serializer_1 = MovieListSerializer(movie_1)
        serializer_2 = MovieListSerializer(movie_2)
        self.assertIn(serializer_2.data, res.data)
        self.assertNotIn(serializer_1.data, res.data)

    def test_filter_movies_by_genre(self):
        movie_without_genres = sample_movie()
        movie_genre_1 = sample_movie(title="title2")
        movie_genre_2 = sample_movie(title="title3")

        genre_1 = sample_genre()
        genre_2 = sample_genre(name="comedy")

        movie_genre_1.genres.add(genre_1)
        movie_genre_2.genres.add(genre_2)

        res = self.client.get(
            MOVIE_URL,
            {"genres": f"{genre_1.id},{genre_2.id}"}
        )

        serializer_without_genre = MovieListSerializer(movie_without_genres)
        serializer_movie_genre_1 = MovieListSerializer(movie_genre_1)
        serializer_movie_genre_2 = MovieListSerializer(movie_genre_2)

        self.assertIn(serializer_movie_genre_1.data, res.data)
        self.assertIn(serializer_movie_genre_2.data, res.data)
        self.assertNotIn(serializer_without_genre.data, res.data)

    def test_filter_movies_by_actors(self):
        movie_without_actors = sample_movie()
        movie_actor_1 = sample_movie(title="title2")
        movie_actor_2 = sample_movie(title="title3")

        actor_1 = sample_actor()
        actor_2 = sample_actor(
            first_name="James",
            last_name="Potter"
        )

        movie_actor_1.actors.add(actor_1)
        movie_actor_2.actors.add(actor_2)

        res = self.client.get(
            MOVIE_URL,
            {"actors": f"{actor_1.id},{actor_2.id}"}
        )

        serializer_without_actors = MovieListSerializer(movie_without_actors)
        serializer_movie_actor_1 = MovieListSerializer(movie_actor_1)
        serializer_movie_actor_2 = MovieListSerializer(movie_actor_2)

        self.assertIn(serializer_movie_actor_1.data, res.data)
        self.assertIn(serializer_movie_actor_2.data, res.data)
        self.assertNotIn(serializer_without_actors.data, res.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()

        url = detail_url(movie.id)

        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "title1",
            "description": "some description",
            "duration": 90,
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@admin.test",
            password="testpassword",
            is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        payload = {
            "title": "title1",
            "description": "some description",
            "duration": 90,
        }

        res = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_create_movie_with_genre_and_actors(self):
        actor_1 = sample_actor()
        actor_2 = sample_actor(
            first_name="James",
            last_name="Potter"
        )
        genre = sample_genre()
        payload = {
            "title": "title1",
            "description": "some description",
            "duration": 90,
            "genres": [genre.id],
            "actors": [actor_1.id, actor_2.id],
        }

        res = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=res.data["id"])
        genres = movie.genres.all()
        actors = movie.actors.all()
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn(genre, genres)
        self.assertIn(actor_1, actors)
        self.assertIn(actor_2, actors)
        self.assertEqual(actors.count(), 2)
