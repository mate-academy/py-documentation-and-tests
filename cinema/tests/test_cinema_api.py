from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from cinema.models import Genre, Actor, Movie
from cinema.serializers import MovieListSerializer, MovieDetailSerializer


MOVIES_URL = reverse("cinema:movie-list")


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


def sample_movie(**params) -> Movie:
    defaults = {
        "title": "Sample movie",
        "description": "Sample description",
        "duration": 90,
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)


class UnauthenticatedCinemaApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIES_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedCinemaApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.test",
            password="testpassword"
        )
        self.client.force_authenticate(self.user)

    def test_movies_list(self):
        sample_movie()

        res = self.client.get(MOVIES_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"], serializer.data)

    def test_retrieve_movie(self):
        movie = sample_movie()
        url = detail_url(movie.id)

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
        res = self.client.post(MOVIES_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminCinemaTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin.user@cinema.com",
            password="1qazcde3",
            is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        genre = Genre.objects.create(name="Drama")
        actor = Actor.objects.create(first_name="George", last_name="Clooney")
        payload = {
            "title": "Sample movie",
            "description": "Sample description",
            "duration": 90,
            "genres": [genre.id],
            "actors": [actor.id]
        }

        res = self.client.post(MOVIES_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        movie = Movie.objects.get()

        for key in ["title", "description", "duration"]:
            self.assertEqual(payload[key], getattr(movie, key))

        self.assertEqual(
            list(movie.genres.values_list(
                "id", flat=True)),
            payload["genres"]
        )
        self.assertEqual(
            list(movie.actors.values_list(
                "id", flat=True)),
            payload["actors"]
        )
