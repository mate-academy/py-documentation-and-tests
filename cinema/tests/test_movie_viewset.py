import os
import tempfile

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from cinema.tests.test_movie_api import (
    MOVIE_URL,
    sample_movie,
    sample_genre,
    sample_actor,
    detail_url, image_upload_url
)


class MoviePermissionsAndBasicTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "user1@myproject.com", "password"
        )
        self.admin = get_user_model().objects.create_superuser(
            "admin2@myproject.com", "password"
        )

        self.genre = sample_genre(name="Action")
        self.actor = sample_actor(first_name="Keanu", last_name="Reeves")

        self.movie = sample_movie(title="Matrix")
        self.movie.genres.add(self.genre)
        self.movie.actors.add(self.actor)

    def test_anon_cannot_get_movie_list(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_user_can_get_movie_list(self):
        self.client.force_authenticate(self.user)
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_authenticated_user_can_get_movie_detail(self):
        self.client.force_authenticate(self.user)
        res = self.client.get(detail_url(self.movie.id))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], self.movie.id)

    def test_non_admin_cannot_create_movie(self):
        self.client.force_authenticate(self.user)
        payload = {
            "title": "Dune",
            "description": "Desc",
            "duration": 155,
            "genres": [self.genre.id],
            "actors": [self.actor.id],
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_create_movie(self):
        self.client.force_authenticate(self.admin)
        payload = {
            "title": "Dune",
            "description": "Desc",
            "duration": 155,
            "genres": [self.genre.id],
            "actors": [self.actor.id],
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["title"], "Dune")


class MovieSerializerSwitchTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "user2@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)

        self.genre = sample_genre(name="Drama")
        self.actor = sample_actor(first_name="Tom", last_name="Hanks")

        self.movie = sample_movie(title="Forrest Gump")
        self.movie.genres.add(self.genre)
        self.movie.actors.add(self.actor)

    def test_movie_list_returns_genres_as_names(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        item = res.data[0]
        self.assertIsInstance(item["genres"], list)
        if item["genres"]:
            self.assertIsInstance(item["genres"][0], str)

    def test_movie_detail_returns_genres_as_objects(self):
        res = self.client.get(detail_url(self.movie.id))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertIsInstance(res.data["genres"], list)
        if res.data["genres"]:
            self.assertIsInstance(res.data["genres"][0], dict)
            self.assertIn("name", res.data["genres"][0])


class MovieFilterTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "user3@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)

        self.g1 = sample_genre(name="Action")
        self.g2 = sample_genre(name="Comedy")

        self.a1 = sample_actor(first_name="Keanu", last_name="Reeves")
        self.a2 = sample_actor(first_name="Jim", last_name="Carrey")

        self.m1 = sample_movie(title="The Matrix")
        self.m1.genres.add(self.g1)
        self.m1.actors.add(self.a1)

        self.m2 = sample_movie(title="Ace Ventura")
        self.m2.genres.add(self.g2)
        self.m2.actors.add(self.a2)

    def test_filter_by_title(self):
        res = self.client.get(MOVIE_URL, {"title": "matrix"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ids = [m["id"] for m in res.data]
        self.assertIn(self.m1.id, ids)
        self.assertNotIn(self.m2.id, ids)

    def test_filter_by_genres(self):
        res = self.client.get(MOVIE_URL, {"genres": str(self.g1.id)})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ids = [m["id"] for m in res.data]
        self.assertIn(self.m1.id, ids)
        self.assertNotIn(self.m2.id, ids)

    def test_filter_by_actors(self):
        res = self.client.get(MOVIE_URL, {"actors": str(self.a2.id)})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ids = [m["id"] for m in res.data]
        self.assertIn(self.m2.id, ids)
        self.assertNotIn(self.m1.id, ids)

    def test_filter_by_multiple_genres_csv(self):
        res = self.client.get(MOVIE_URL, {"genres": f"{self.g1.id},{self.g2.id}"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ids = [m["id"] for m in res.data]
        self.assertIn(self.m1.id, ids)
        self.assertIn(self.m2.id, ids)


class MovieUploadImagePermissionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "user4@myproject.com", "password"
        )
        self.admin = get_user_model().objects.create_superuser(
            "admin-upload@myproject.com", "password"
        )
        self.movie = sample_movie()

    def test_non_admin_cannot_upload_image(self):
        self.client.force_authenticate(self.user)
        url = image_upload_url(self.movie.id)

        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(url, {"image": ntf}, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_upload_image(self):
        self.client.force_authenticate(self.admin)
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
