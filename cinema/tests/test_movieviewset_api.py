from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient
from django.test import TestCase

from cinema.models import Movie, Genre, Actor
from cinema.serializers import (
    MovieListSerializer,
    MovieDetailSerializer
)

MOVIE_URL = reverse("cinema:movie-list")

def sample_movie(**params) -> Movie:
    defaults = {
        "title": "Sample movie",
        "description": "Sample description",
        "duration": 90,
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)


class UnauthenticatedMovieViewSetTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieViewSetTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin.user@cinema.com", password="1qazcde3"
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
        movie1 = sample_movie()
        movie1.title = "Inception"
        movie1.save()

        movie2 = sample_movie()
        movie2.title = "Titanic"
        movie2.save()

        res = self.client.get(
            MOVIE_URL,
            {"title": "Inception"}
        )

        serializer = MovieListSerializer(
            [movie1],
            many=True
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_genres(self):
        genre1 = Genre.objects.create(name="Action")
        genre2 = Genre.objects.create(name="Comedy")

        movie1 = sample_movie()
        movie1.genres.add(genre1)

        movie2 = sample_movie()
        movie2.genres.add(genre2)

        res = self.client.get(
            MOVIE_URL,
            {"genres": genre1.id}
        )

        serializer = MovieListSerializer(
            [movie1],
            many=True
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_actors(self):
        actor1 = Actor.objects.create(
            first_name="Tom",
            last_name="Hanks",
        )
        actor2 = Actor.objects.create(
            first_name="Brad",
            last_name="Pitt",
        )

        movie1 = sample_movie()
        movie1.actors.add(actor1)

        movie2 = sample_movie()
        movie2.actors.add(actor2)

        res = self.client.get(
            MOVIE_URL,
            {"actors": actor1.id}
        )

        serializer = MovieListSerializer(
            [movie1],
            many=True
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_retrieve_detail_movie(self):
        movie = sample_movie()
        url = reverse(
            "cinema:movie-detail",
            args=[movie.id],
        )
        res = self.client.get(url)
        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Sample movie",
            "description": "Sample description",
            "duration": 90,
        }

        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin.user@cinema.com",
            password="1qazcde3",
            is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        genre = Genre.objects.create(name="Action")
        actor = Actor.objects.create(
            first_name="Tom",
            last_name="Hanks",
        )

        payload = {
            "title": "Sample movie",
            "description": "Sample description",
            "duration": 90,
            "genres": [genre.id],
            "actors": [actor.id],
        }

        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        movie = Movie.objects.get(id=res.data["id"])
        self.assertEqual(movie.title, payload["title"])
        self.assertEqual(movie.description, payload["description"])
        self.assertEqual(movie.duration, payload["duration"])
