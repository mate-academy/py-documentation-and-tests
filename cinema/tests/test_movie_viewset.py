from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from .test_movie_api import (
    sample_movie,
    sample_genre,
    sample_actor,
    MOVIE_URL,
    detail_url,
    image_upload_url,
)

from cinema.models import Movie
import os
import tempfile
from PIL import Image


class MovieViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_list_movies(self):
        sample_movie(title="Alpha")
        sample_movie(title="Beta")

        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)

    def test_filter_movies_by_title(self):
        sample_movie(title="Star Wars")
        sample_movie(title="Other")

        res = self.client.get(MOVIE_URL, {"title": "Star"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)

    def test_filter_movies_by_genres(self):
        g1 = sample_genre(name="Action")
        g2 = sample_genre(name="Drama")

        m1 = sample_movie(title="M1")
        m1.genres.add(g1)
        m2 = sample_movie(title="M2")
        m2.genres.add(g2)

        res = self.client.get(MOVIE_URL, {"genres": f"{g1.id}"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)

    def test_filter_movies_by_actors(self):
        a1 = sample_actor(first_name="Tom", last_name="Cruise")
        a2 = sample_actor(first_name="Brad", last_name="Pitt")

        m1 = sample_movie(title="M1")
        m1.actors.add(a1)
        m2 = sample_movie(title="M2")
        m2.actors.add(a2)

        res = self.client.get(MOVIE_URL, {"actors": f"{a1.id}"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)

    def test_retrieve_movie_detail_contains_relations(self):
        m = sample_movie(title="Full")
        g = sample_genre(name="G1")
        a = sample_actor()
        m.genres.add(g)
        m.actors.add(a)

        res = self.client.get(detail_url(m.id))

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["title"], m.title)
        self.assertIn("genres", res.data)
        self.assertIn("actors", res.data)

    def test_non_admin_cannot_upload_image(self):
        user = get_user_model().objects.create_user("user@example.com", "testpass")
        self.client.force_authenticate(user)
        movie = sample_movie()

        url = image_upload_url(movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(url, {"image": ntf}, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_create_movie(self):
        user = get_user_model().objects.create_superuser("admin@example.com", "testpass")
        self.client.force_authenticate(user)
        g = sample_genre(name="Action")
        a = sample_actor(first_name="First", last_name="Last")
        payload = {
            "title": "Created Movie",
            "description": "Desc",
            "duration": 120,
            "genres": [g.id],
            "actors": [a.id],
        }
        res = self.client.post(MOVIE_URL, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Movie.objects.filter(title="Created Movie").exists())

    def test_non_admin_cannot_create_movie(self):
        user = get_user_model().objects.create_user("user2@example.com", "testpass")
        self.client.force_authenticate(user)
        g = sample_genre()
        a = sample_actor()
        payload = {
            "title": "No Create",
            "description": "Desc",
            "duration": 90,
            "genres": [g.id],
            "actors": [a.id],
        }
        res = self.client.post(MOVIE_URL, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_upload_image(self):
        user = get_user_model().objects.create_superuser("admin2@example.com", "password")
        self.client.force_authenticate(user)
        movie = sample_movie()
        url = image_upload_url(movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(url, {"image": ntf}, format="multipart")
        movie.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)
        self.assertTrue(os.path.exists(movie.image.path))
        movie.image.delete()
