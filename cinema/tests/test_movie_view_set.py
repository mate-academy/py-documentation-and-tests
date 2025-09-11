import os
import tempfile
from unittest import TestCase

from PIL import Image
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from cinema.models import Genre, Actor, Movie

MOVIE_URL = reverse("cinema:movie-list")


def sample_genre(name="Drama"):
    return Genre.objects.create(name=name)


def sample_actor(name="Vasya Pupkin"):
    return Actor.objects.create(full_name=name)


def sample_movie(**params):
    defaults = {
        "title": "Hot Fuzz",
        "description": "Simon Peg the best",
        "duration": 120,
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)


class TestMovieViewSet(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            "user@user.com",
            "password123"
        )
        self.admin = get_user_model().objects.create_superuser(
            "admin@admin.com",
            "password123"
        )

    def test_list_movies(self):
        movie1 = sample_movie(title="First Movie")
        movie2 = sample_movie(title="Second Movie")

        self.client.force_authenticate(user=self.user)

        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)
        movies = [movie["title"] for movie in res.data]
        self.assertIn(movie1.title, movies)
        self.assertIn(movie2.title, movies)

    def test_filter_movies_by_title(self):
        movie1 = sample_movie(title="Skajene Vesilya")
        sample_movie(title="Avatar")

        self.client.force_authenticate(user=self.user)

        res = self.client.get(MOVIE_URL, {"title": "Skajene Vesilya"})

        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], movie1.title)

    def test_filter_movies_by_genres(self):
        ukrainian = Genre.objects.create(name="Ukrainian")
        comedy = Genre.objects.create(name="Comedy")

        movie1 = sample_movie(title="Skajene Vesilya")
        movie1.genres.add(ukrainian, comedy)

        movie2 = sample_movie(title="Avatar")
        movie2.genres.add(comedy)

        self.client.force_authenticate(user=self.user)

        res = self.client.get(MOVIE_URL, {"genres": ukrainian.id})

        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], movie1.title)

        res = self.client.get(MOVIE_URL, {"genres": f"{ukrainian.id}, {comedy.id}"})

        self.assertEqual(len(res.data), 2)
        self.assertEqual(res.data[0]["title"], movie2.title)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        url = reverse("cinema:movie-detail", args=[movie.id])

        self.client.force_authenticate(user=self.user)

        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], movie.id)
        self.assertEqual(res.data["title"], movie.title)

    def test_create_movie_as_admin(self):
        genre = Genre.objects.create(name="Test")
        actor = Actor.objects.create(first_name="Test", last_name="Actor")
        self.client.force_authenticate(user=self.admin)
        payload = {
            "title": "New Movie",
            "description": "Cool movie",
            "duration": 150,
            "genres": genre.id,
            "actors": actor.id,
        }
        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Movie.objects.filter(title="New Movie").exists())

    def test_create_movie_as_user_forbidden(self):
        self.client.force_authenticate(user=self.user)
        payload = {
            "title": "Forbidden Movie",
            "description": "takoe",
            "duration": 100,
        }
        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_upload_image_to_movie(self):
        self.client.force_authenticate(user=self.admin)
        movie = sample_movie()
        url = reverse("cinema:movie-upload-image", args=[movie.id])

        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(url, {"image": ntf}, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        movie.refresh_from_db()
        self.assertTrue(os.path.exists(movie.image.path))
