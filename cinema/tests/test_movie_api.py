from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
import tempfile
import os
from PIL import Image

from cinema.models import Movie, CinemaHall, Genre, Actor

MOVIE_URL = reverse("cinema:movie-list")


def sample_movie(**params):
    defaults = {"title": "Sample", "description": "Desc", "duration": 90}
    defaults.update(params)
    return Movie.objects.create(**defaults)


def sample_genre(**params):
    defaults = {"name": "Drama"}
    defaults.update(params)
    return Genre.objects.create(**defaults)


def sample_actor(**params):
    defaults = {"first_name": "George", "last_name": "Clooney"}
    defaults.update(params)
    return Actor.objects.create(**defaults)


class MovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user("u@u.com", "pass")
        self.admin = get_user_model().objects.create_superuser("a@a.com", "pass")
        self.client.force_authenticate(self.user)
        self.movie1 = sample_movie(title="Movie 1")
        self.genre1 = sample_genre()
        self.actor1 = sample_actor()
        self.movie1.genres.add(self.genre1)
        self.movie1.actors.add(self.actor1)

    def test_list_movies(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_filter_movies_by_title(self):
        res = self.client.get(MOVIE_URL, {"title": "Movie 1"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_create_movie_by_admin(self):
        self.client.force_authenticate(self.admin)
        payload = {
            "title": "New", "description": "D", "duration": 100,
            "genres": [self.genre1.id], "actors": [self.actor1.id]
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_create_movie_by_user_forbidden(self):
        payload = {"title": "New", "description": "D", "duration": 100}
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class MovieImageUploadTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = get_user_model().objects.create_superuser("a@a.com", "pass")
        self.client.force_authenticate(self.admin)
        self.movie = sample_movie()

    def tearDown(self):
        self.movie.image.delete()

    def test_upload_image(self):
        url = reverse("cinema:movie-upload-image", args=[self.movie.id])
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(url, {"image": ntf}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_upload_invalid_image(self):
        url = reverse("cinema:movie-upload-image", args=[self.movie.id])
        res = self.client.post(url, {"image": "not image"}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
