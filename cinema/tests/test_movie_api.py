import tempfile
import os
from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")


def sample_movie(**params):
    defaults = {
        "title": "Sample movie",
        "description": "Sample description",
        "duration": 90,
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@test.com", "testpass"
        )
        self.client.force_authenticate(self.user)

    def test_filter_movies_by_actors(self):
        movie1 = sample_movie(title="Movie 1")
        movie2 = sample_movie(title="Movie 2")
        actor1 = Actor.objects.create(first_name="Actor", last_name="1")
        actor2 = Actor.objects.create(first_name="Actor", last_name="2")
        movie1.actors.add(actor1)
        movie2.actors.add(actor2)

        res = self.client.get(MOVIE_URL, {"actors": f"{actor1.id}"})

        self.assertIn(MovieListSerializer(movie1).data, res.data)
        self.assertNotIn(MovieListSerializer(movie2).data, res.data)

    def test_create_movie_forbidden(self):
        payload = {"title": "Movie", "description": "D", "duration": 100}
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_put_movie_forbidden(self):
        movie = sample_movie()
        payload = {"title": "New Title", "description": "D", "duration": 100}
        url = detail_url(movie.id)
        res = self.client.put(url, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_patch_movie_forbidden(self):
        movie = sample_movie()
        payload = {"title": "New Title"}
        url = detail_url(movie.id)
        res = self.client.patch(url, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_upload_image_forbidden(self):
        movie = sample_movie()
        url = reverse("cinema:movie-upload-image", args=[movie.id])
        res = self.client.post(url, {"image": "some_image"}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@test.com", "adminpass"
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        genre = Genre.objects.create(name="Drama")
        actor = Actor.objects.create(first_name="John", last_name="Doe")
        payload = {
            "title": "Movie",
            "description": "Description",
            "duration": 100,
            "genres": [genre.id],
            "actors": [actor.id],
        }
        res = self.client.post(MOVIE_URL, payload)

        if res.status_code != status.HTTP_201_CREATED:
            print(res.data)  # Додано для налагодження, як просив рев'юер

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_update_movie(self):
        movie = sample_movie()
        genre = Genre.objects.create(name="Action")
        payload = {
            "title": "Updated Title",
            "description": "Updated description",
            "duration": 120,
            "genres": [genre.id],
            "actors": [],
        }
        url = detail_url(movie.id)
        res = self.client.put(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        movie.refresh_from_db()
        self.assertEqual(movie.title, payload["title"])

    def test_upload_image_to_movie(self):
        movie = sample_movie()
        url = reverse("cinema:movie-upload-image", args=[movie.id])
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(url, {"image": ntf}, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)
        movie.refresh_from_db()
        self.assertTrue(os.path.exists(movie.image.path))
