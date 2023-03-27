import os
import tempfile

from PIL import Image
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from cinema.models import Movie, Genre, Actor
from cinema.serializers import (
    MovieListSerializer,
    MovieDetailSerializer,
    MovieSerializer,
)

MOVIE_URL = reverse("cinema:movie-list")


def retrieve_movie_url(pk: int = 1) -> str:
    return reverse("cinema:movie-detail", args=[pk])


class TestUnauthenticatedMovieApi(APITestCase):
    def setUp(self) -> None:
        self.client = self.client_class()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class TestAuthenticatedMovieApi(APITestCase):
    def setUp(self) -> None:
        self.client = self.client_class()
        user = get_user_model().objects.create_user("test@test.com", "test1234")
        self.client.force_authenticate(user)
        self.movie1 = Movie.objects.create(title="1", description="1", duration=1)
        self.movie2 = Movie.objects.create(title="2", description="2", duration=2)
        self.movie3 = Movie.objects.create(title="3", description="3", duration=3)

    def test_list_movie(self):
        res = self.client.get(MOVIE_URL)
        serializer = MovieListSerializer(Movie.objects.all(), many=True)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data, serializer.data)

    def test_filter_list_movie(self):
        genre1 = Genre.objects.create(name="drama")
        genre2 = Genre.objects.create(name="horror")
        actor1 = Actor.objects.create(first_name="1", last_name="2")
        actor2 = Actor.objects.create(first_name="3", last_name="4")
        self.movie1.genres.add(genre1)
        self.movie2.genres.add(genre2)
        self.movie3.genres.add(genre2, genre1)
        self.movie1.actors.add(actor1)
        self.movie2.actors.add(actor2)
        self.movie3.actors.add(actor1, actor2)
        serializer1 = MovieListSerializer(self.movie1)
        serializer2 = MovieListSerializer(self.movie2)
        serializer3 = MovieListSerializer(self.movie3)

        res = self.client.get(MOVIE_URL, {"title": "2"})
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer1.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

        res = self.client.get(MOVIE_URL, {"genres": [1]})
        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)
        self.assertIn(serializer3.data, res.data)

        res = self.client.get(MOVIE_URL, {"actors": [2]})
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer1.data, res.data)
        self.assertIn(serializer3.data, res.data)

    def test_retrieve_movie(self):
        res = self.client.get(retrieve_movie_url())
        serializer = MovieDetailSerializer(self.movie1)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        data = {"title": "3", "description": "3", "duration": 3}
        res = self.client.post(MOVIE_URL, data)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class TestAdminMovieApi(APITestCase):
    def setUp(self) -> None:
        self.client = self.client_class()
        user = get_user_model().objects.create_user(
            "test@test.com", "test1234", is_staff=True
        )
        self.client.force_authenticate(user)
        self.movie = Movie.objects.create(title="1", description="1", duration=1)

    def test_create_movie(self):
        genre1 = Genre.objects.create(name="horror")
        actor1 = Actor.objects.create(first_name="1", last_name="2")
        data = {
            "title": "3",
            "description": "3",
            "duration": 3,
            "actors": [1],
            "genres": [1],
        }
        res = self.client.post(MOVIE_URL, data)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        for key, value in data.items():
            self.assertEqual(res.data[key], value)

    def test_upload_image(self):
        url = reverse("cinema:movie-upload-image", args=[self.movie.id])
        with tempfile.NamedTemporaryFile(suffix=".jpg") as tmp_file:
            img = Image.new("RGB", (100, 100))
            img.save(tmp_file, format="JPEG")
            tmp_file.seek(0)
            res = self.client.post(url, {"image": tmp_file}, format="multipart")
        self.movie.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)

    def test_upload_image_with_errors(self):
        url = reverse("cinema:movie-upload-image", args=[self.movie.id])
        res = self.client.post(url, {"image": "img"}, format="multipart")
        self.movie.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
