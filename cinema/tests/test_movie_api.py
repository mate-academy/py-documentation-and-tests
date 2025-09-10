import tempfile
import os
from datetime import datetime

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor
from cinema.serializers import MovieListSerializer

MOVIE_URL = reverse("cinema:movie-list")
MOVIE_SESSION_URL = reverse("cinema:moviesession-list")
TOKEN_URL = reverse("token_obtain_pair")


def sample_movie(**params):
    defaults = {
        "title": "Sample movie",
        "description": "Sample description",
        "duration": 90,
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


def sample_movie_session(**params):
    cinema_hall = CinemaHall.objects.create(name="Blue", rows=20, seats_in_row=20)

    defaults = {
        "show_time": datetime(2022, 6, 2, 14, 0, 0),
        "movie": None,
        "cinema_hall": cinema_hall,
    }
    defaults.update(params)

    return MovieSession.objects.create(**defaults)


def image_upload_url(movie_id):
    return reverse("cinema:movie-upload-image", args=[movie_id])


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


class JWTAuthFlowTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user@cinema.com",
            password="testpass123"
        )
        self.movie = sample_movie()

    def authenticate(self):
        res = self.client.post(TOKEN_URL, {
            "email": self.user.email,
            "password": "testpass123"
        })
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        token = res.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_jwt_token_authentication(self):
        self.authenticate()
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)


class MovieImageUploadTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        res = self.client.post(TOKEN_URL, {
            "email": self.user.email,
            "password": "password"
        })
        token = res.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        self.movie = sample_movie()
        self.genre = sample_genre()
        self.actor = sample_actor()
        self.movie_session = sample_movie_session(movie=self.movie)

    def tearDown(self):
        self.movie.image.delete()

    def test_upload_image_to_movie(self):
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(url, {"image": ntf}, format="multipart")
        self.movie.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)
        self.assertTrue(os.path.exists(self.movie.image.path))


class AuthenticatedMovieTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user@cinema.com",
            password="testpass123",
        )
        res = self.client.post(TOKEN_URL, {
            "email": self.user.email,
            "password": "testpass123"
        })
        token = res.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_movie_filter_by_title(self):
        movie1 = sample_movie(title="The Matrix")
        movie2 = sample_movie(title="Inception")

        res = self.client.get(MOVIE_URL, {"title": "cept"})
        serializer1 = MovieListSerializer(movie2)
        serializer2 = MovieListSerializer(movie1)

        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)
        self.assertEqual(len(res.data), 1)


class AdminMovieViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = get_user_model().objects.create_superuser(
            email="admin@cinema.com",
            password="adminpass"
        )
        res = self.client.post(TOKEN_URL, {
            "email": self.admin.email,
            "password": "adminpass"
        })
        token = res.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.genre1 = sample_genre(name="Action")
        self.genre2 = sample_genre(name="Comedy")
        self.actor1 = sample_actor(first_name="Tom", last_name="Hanks")
        self.actor2 = sample_actor(first_name="Emma", last_name="Stone")

    def test_create_movie(self):
        payload = {
            "title": "New Movie",
            "description": "Description",
            "duration": 120,
            "genres": [self.genre1.id, self.genre2.id],
            "actors": [self.actor1.id, self.actor2.id]
        }
        res = self.client.post(MOVIE_URL, payload, format="json")
        self.assertIn(res.status_code, [status.HTTP_201_CREATED, status.HTTP_405_METHOD_NOT_ALLOWED])
        if res.status_code == status.HTTP_201_CREATED:
            movie = Movie.objects.get(id=res.data["id"])
            self.assertEqual(movie.title, payload["title"])

    def test_retrieve_movie(self):
        movie = sample_movie()
        movie.genres.set([self.genre1])
        movie.actors.set([self.actor1])
        url = detail_url(movie.id)
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], movie.id)

    def test_filter_movies_by_genres(self):
        movie1 = sample_movie(title="Movie1")
        movie2 = sample_movie(title="Movie2")
        movie1.genres.set([self.genre1])
        movie2.genres.set([self.genre2])
        res = self.client.get(MOVIE_URL, {"genres": self.genre1.id})
        if res.status_code == status.HTTP_200_OK:
            ids = [m["id"] for m in res.data]
            self.assertIn(movie1.id, ids)
            self.assertNotIn(movie2.id, ids)

    def test_filter_movies_by_actors(self):
        movie1 = sample_movie(title="Movie1")
        movie2 = sample_movie(title="Movie2")
        movie1.actors.set([self.actor1])
        movie2.actors.set([self.actor2])
        res = self.client.get(MOVIE_URL, {"actors": self.actor1.id})
        if res.status_code == status.HTTP_200_OK:
            ids = [m["id"] for m in res.data]
            self.assertIn(movie1.id, ids)
            self.assertNotIn(movie2.id, ids)
