from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from rest_framework.test import APIClient

from cinema.models import Movie, Actor, Genre
from cinema.serializers import (
    MovieListSerializer,
    MovieDetailSerializer,
)

MOVIE_URL = reverse("cinema:movie-list")


def detail_url(movie_id: int):
    return reverse("cinema:movie-detail", args=[movie_id])


def sample_movie(**params):
    defaults = {
        "title": "Sample movie",
        "description": "Sample description",
        "duration": 90,
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
            "test@test.com",
            "testpass123",
        )
        self.client.force_authenticate(self.user)

    def test_list_movies(self):
        sample_movie()
        movie_with_actors_and_genres = sample_movie()

        actor1 = Actor.objects.create(first_name="George", last_name="Clooney")
        actor2 = Actor.objects.create(first_name="Brad", last_name="Pitt")

        genre1 = Genre.objects.create(name="Drama")
        genre2 = Genre.objects.create(name="Comedy")

        movie_with_actors_and_genres.actors.add(actor1, actor2)
        movie_with_actors_and_genres.genres.add(genre1, genre2)

        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_title(self):
        movie1 = sample_movie(title="Garry Potter")
        movie2 = sample_movie(title="Pianist")

        res = self.client.get(MOVIE_URL, {"title": "Pianist"})

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)

        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer1.data, res.data)

    def test_filter_movies_by_genres(self):
        movie1 = sample_movie(title="Garry Potter")
        movie2 = sample_movie(title="Pianist")

        genre1 = Genre.objects.create(name="Detective")
        genre2 = Genre.objects.create(name="Drama")

        movie1.genres.add(genre1)
        movie2.genres.add(genre2)

        movie3 = sample_movie(title="Batman")

        res = self.client.get(MOVIE_URL, {"genres": f"{genre1.id},{genre2.id}"})

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie3)

        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_filter_movies_by_actors(self):
        movie1 = sample_movie(title="Garry Potter")
        movie2 = sample_movie(title="Pianist")

        actor1 = Actor.objects.create(first_name="Alec", last_name="Baldwin")
        actor2 = Actor.objects.create(first_name="Kim", last_name="Basinger")

        movie1.actors.add(actor1)
        movie2.actors.add(actor2)

        movie3 = sample_movie(title="Batman")

        res = self.client.get(MOVIE_URL, {"actors": f"{actor1.id},{actor2.id}"})

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie3)

        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        movie.genres.add(Genre.objects.create(name="Drama"))
        movie.actors.add(Actor.objects.create(first_name="Pamela", last_name="Anderson"))

        url = detail_url(movie.id)
        res = self.client.get(url)
        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Unbreakable",
            "description": "Dramatically action film",
            "duration": 120
        }
        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@admin.com",
            "testpass12345",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        payload = {
            "title": "Unbreakable",
            "description": "Dramatically action film",
            "duration": 120
        }
        res = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_create_movie_with_genres_and_actors(self):
        actor1 = Actor.objects.create(first_name="George", last_name="Clooney")
        actor2 = Actor.objects.create(first_name="Brad", last_name="Pitt")
        genre1 = Genre.objects.create(name="Drama")
        genre2 = Genre.objects.create(name="Comedy")

        payload = {
            "title": "Unbreakable",
            "description": "Dramatically action film",
            "duration": 120,
            "genres": [genre1.id, genre2.id],
            "actors": [actor1.id, actor2.id]
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

    def test_delete_movie_not_allowed(self):
        movie = sample_movie()
        url = detail_url(movie.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
