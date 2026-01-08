import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor

MOVIE_URL = reverse("cinema:movie-list")


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


def sample_movie(**params):
    defaults = {
        "title": "Sample",
        "description": "Desc",
        "duration": 90
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)


class UnauthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_movie_unauthenticated_denied(self):
        movie = sample_movie()
        res = self.client.get(detail_url(movie.id))
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_upload_image_unauthenticated_denied(self):
        movie = sample_movie()
        url = reverse("cinema:movie-upload-image", args=[movie.id])
        res = self.client.post(url, {"image": "test"}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@test.com",
            "pass12345"
        )
        self.client.force_authenticate(self.user)

    def test_list_movies(self):
        sample_movie()
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        res = self.client.get(detail_url(movie.id))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_create_movie_forbidden(self):
        payload = {"title": "Forbidden", "duration": 100}
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_upload_image_forbidden(self):
        movie = sample_movie()
        url = reverse("cinema:movie-upload-image", args=[movie.id])
        res = self.client.post(url, {"image": "test"}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@test.com",
            "pass12345"
        )
        self.client.force_authenticate(self.user)
        self.movie = sample_movie()

    def test_create_movie_success(self):
        genre = Genre.objects.create(name="Drama")
        actor = Actor.objects.create(first_name="A", last_name="B")
        payload = {
            "title": "New Movie",
            "description": "Desc",
            "duration": 120,
            "genres": [genre.id],
            "actors": [actor.id]
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_retrieve_movie_admin(self):
        res = self.client.get(detail_url(self.movie.id))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_upload_image_to_movie(self):
        url = reverse("cinema:movie-upload-image", args=[self.movie.id])
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(url, {"image": ntf}, format="multipart")

        self.movie.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(os.path.exists(self.movie.image.path))
        self.movie.image.delete()