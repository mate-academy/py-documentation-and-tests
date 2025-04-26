from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from decimal import Decimal
from PIL import Image
import tempfile
import os

from cinema.models import Movie, Genre, Actor
from cinema.serializers import (
    MovieSerializer,
    MovieDetailSerializer,
    MovieListSerializer,
    MovieImageSerializer,
)
from cinema.views import MovieViewSet


class MovieViewSetTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user@example.com", password="testpass123"
        )
        self.admin_user = get_user_model().objects.create_superuser(
            email="admin@example.com", password="testpass123"
        )
        self.client.force_authenticate(self.user)

        self.genre1 = Genre.objects.create(name="Action")
        self.genre2 = Genre.objects.create(name="Drama")

        self.actor1 = Actor.objects.create(first_name="Tom", last_name="Cruise")
        self.actor2 = Actor.objects.create(first_name="Brad", last_name="Pitt")

        self.movie1 = Movie.objects.create(
            title="Mission Impossible", description="Action movie", duration=120
        )
        self.movie1.genres.add(self.genre1)
        self.movie1.actors.add(self.actor1)

        self.movie2 = Movie.objects.create(
            title="Fight Club", description="Drama movie", duration=130
        )
        self.movie2.genres.add(self.genre2)
        self.movie2.actors.add(self.actor2)

        self.movie3 = Movie.objects.create(
            title="Avengers", description="Superhero movie", duration=140
        )
        self.movie3.genres.add(self.genre1)
        self.movie3.actors.add(self.actor1, self.actor2)

        self.movies_url = reverse("cinema:movie-list")

    def test_list_movies(self):
        response = self.client.get(self.movies_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

    def test_filter_movies_by_title(self):
        response = self.client.get(f"{self.movies_url}?title=avengers")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Avengers")

    def test_filter_movies_by_genres(self):
        response = self.client.get(f"{self.movies_url}?genres={self.genre1.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_filter_movies_by_actors(self):
        response = self.client.get(f"{self.movies_url}?actors={self.actor2.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_retrieve_movie_detail(self):
        url = reverse("cinema:movie-detail", args=[self.movie1.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], self.movie1.title)
        self.assertIn("genres", response.data)
        self.assertIn("actors", response.data)

    def test_create_movie_unauthorized(self):
        self.client.logout()
        payload = {
            "title": "New Movie",
            "description": "New description",
            "duration": 110,
            "genres": [self.genre1.id],
            "actors": [self.actor1.id],
        }

        response = self.client.post(self.movies_url, payload)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_movie_by_regular_user(self):
        self.client.force_authenticate(self.user)
        payload = {
            "title": "New Movie",
            "description": "New description",
            "duration": 110,
            "genres": [self.genre1.id],
            "actors": [self.actor1.id],
        }

        response = self.client.post(self.movies_url, payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_movie_by_admin(self):
        self.client.force_authenticate(self.admin_user)
        payload = {
            "title": "New Movie",
            "description": "New description",
            "duration": 110,
            "genres": [self.genre1.id],
            "actors": [self.actor1.id],
        }

        response = self.client.post(self.movies_url, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertTrue(Movie.objects.filter(title="New Movie").exists())

    def test_upload_image(self):
        self.client.force_authenticate(self.admin_user)

        url = reverse("cinema:movie-upload-image", args=[self.movie1.id])

        with tempfile.NamedTemporaryFile(suffix=".jpg") as image_file:
            img = Image.new("RGB", (10, 10))
            img.save(image_file, format="JPEG")
            image_file.seek(0)

            payload = {"image": image_file}
            response = self.client.post(url, payload, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.movie1.refresh_from_db()

        self.assertIn("image", response.data)
        self.assertTrue(response.data["image"])
        self.assertTrue(self.movie1.image)

        if os.path.exists(self.movie1.image.path):
            os.remove(self.movie1.image.path)

    def test_upload_image_unauthorized(self):
        self.client.logout()

        url = reverse("cinema:movie-upload-image", args=[self.movie1.id])

        with tempfile.NamedTemporaryFile(suffix=".jpg") as image_file:
            img = Image.new("RGB", (10, 10))
            img.save(image_file, format="JPEG")
            image_file.seek(0)

            payload = {"image": image_file}
            response = self.client.post(url, payload, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_upload_image_by_regular_user(self):
        self.client.force_authenticate(self.user)

        url = reverse("cinema:movie-upload-image", args=[self.movie1.id])

        with tempfile.NamedTemporaryFile(suffix=".jpg") as image_file:
            img = Image.new("RGB", (10, 10))
            img.save(image_file, format="JPEG")
            image_file.seek(0)

            payload = {"image": image_file}
            response = self.client.post(url, payload, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_params_to_ints_method(self):

        viewset = MovieViewSet()
        result = viewset._params_to_ints("1,2,3")

        self.assertEqual(result, [1, 2, 3])

    def test_get_serializer_class(self):

        viewset = MovieViewSet()

        viewset.action = "list"
        self.assertEqual(viewset.get_serializer_class(), MovieListSerializer)

        viewset.action = "retrieve"
        self.assertEqual(viewset.get_serializer_class(), MovieDetailSerializer)

        viewset.action = "create"
        self.assertEqual(viewset.get_serializer_class(), MovieSerializer)

        viewset.action = "upload_image"
        self.assertEqual(viewset.get_serializer_class(), MovieImageSerializer)
