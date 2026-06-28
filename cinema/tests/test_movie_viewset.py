import os
import tempfile

from PIL import Image

from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from user.models import User


MOVIE_URL = reverse("cinema:movie-list")


def image_upload_url(movie_id):
    return reverse("cinema:movie-upload-image", args=[movie_id])


class MovieViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
        )

        self.admin = User.objects.create_superuser(
            email="admin@test.com",
            password="adminpass123",
        )

        self.genre = Genre.objects.create(name="Action")
        self.actor = Actor.objects.create(
            first_name="Tom",
            last_name="Hanks",
        )

        self.movie = Movie.objects.create(
            title="Test Movie",
            description="Test description",
            duration=120,
        )

        self.movie.genres.add(self.genre)
        self.movie.actors.add(self.actor)

    def tearDown(self):
        if self.movie.image:
            self.movie.image.delete()

    def auth_user(self):
        self.client.force_authenticate(user=self.user)

    def auth_admin(self):
        self.client.force_authenticate(user=self.admin)

    def test_list_movies(self):
        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(res.data), 1)

    def test_list_uses_list_serializer(self):
        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        movie = res.data[0]

        self.assertEqual(movie["genres"], ["Action"])
        self.assertEqual(movie["actors"], ["Tom Hanks"])

    def test_retrieve_movie(self):
        url = reverse("cinema:movie-detail", args=[self.movie.id])

        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], self.movie.id)

    def test_retrieve_uses_detail_serializer(self):
        url = reverse("cinema:movie-detail", args=[self.movie.id])

        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertEqual(
            res.data["genres"],
            [
                {
                    "id": self.genre.id,
                    "name": "Action",
                }
            ],
        )

        self.assertEqual(
            res.data["actors"],
            [
                {
                    "id": self.actor.id,
                    "first_name": "Tom",
                    "last_name": "Hanks",
                    "full_name": "Tom Hanks",
                }
            ],
        )

    def test_create_movie_admin(self):
        self.auth_admin()

        payload = {
            "title": "New Movie",
            "description": "Some description",
            "duration": 100,
            "genres": [self.genre.id],
            "actors": [self.actor.id],
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Movie.objects.filter(title="New Movie").exists())

    def test_create_movie_forbidden(self):
        self.auth_user()

        payload = {
            "title": "Bad Movie",
            "description": "Some description",
            "duration": 100,
            "genres": [self.genre.id],
            "actors": [self.actor.id],
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_movie_anon(self):
        payload = {
            "title": "Anon Movie",
            "description": "Some description",
            "duration": 100,
            "genres": [self.genre.id],
            "actors": [self.actor.id],
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_filter_by_title(self):
        res = self.client.get(MOVIE_URL, {"title": "Test"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(res.data), 1)

    def test_filter_by_genre(self):
        res = self.client.get(MOVIE_URL, {"genres": self.genre.id})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(res.data), 1)

    def test_filter_by_actor(self):
        res = self.client.get(MOVIE_URL, {"actors": self.actor.id})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(res.data), 1)

    def test_upload_image_admin(self):
        self.auth_admin()

        url = image_upload_url(self.movie.id)

        with tempfile.NamedTemporaryFile(suffix=".jpg") as image_file:
            img = Image.new("RGB", (10, 10))
            img.save(image_file, format="JPEG")
            image_file.seek(0)

            res = self.client.post(
                url,
                {"image": image_file},
                format="multipart",
            )

        self.movie.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(self.movie.image)
        self.assertTrue(os.path.exists(self.movie.image.path))

    def test_upload_image_forbidden(self):
        self.auth_user()

        url = image_upload_url(self.movie.id)

        with tempfile.NamedTemporaryFile(suffix=".jpg") as image_file:
            img = Image.new("RGB", (10, 10))
            img.save(image_file, format="JPEG")
            image_file.seek(0)

            res = self.client.post(
                url,
                {"image": image_file},
                format="multipart",
            )

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_upload_image_anon(self):
        url = image_upload_url(self.movie.id)

        with tempfile.NamedTemporaryFile(suffix=".jpg") as image_file:
            img = Image.new("RGB", (10, 10))
            img.save(image_file, format="JPEG")
            image_file.seek(0)

            res = self.client.post(
                url,
                {"image": image_file},
                format="multipart",
            )

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
