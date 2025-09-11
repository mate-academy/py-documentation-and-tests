import tempfile
import os
from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from cinema.models import Movie, Genre, Actor


def sample_movie(**params):
    defaults = {
        "title": "Sample movie",
        "description": "Sample description",
        "duration": 90,
    }
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


def image_upload_url(movie_id):
    return reverse("cinema:movie-upload-image", args=[movie_id])


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


class MovieViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@example.com", password="testpass123"
        )
        self.admin_user = get_user_model().objects.create_superuser(
            email="admin@example.com", password="adminpass123"
        )
        self.movie = sample_movie()
        self.genre = sample_genre()
        self.actor = sample_actor()
        self.movie.genres.add(self.genre)
        self.movie.actors.add(self.actor)

    def test_list_movies_unauthorized(self):
        url = reverse("cinema:movie-list")
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], self.movie.title)

    def test_retrieve_movie_detail(self):
        url = detail_url(self.movie.id)
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["title"], self.movie.title)
        self.assertEqual(len(res.data["genres"]), 1)
        self.assertEqual(len(res.data["actors"]), 1)

    def test_create_movie_unauthorized(self):
        url = reverse("cinema:movie-list")
        payload = {
            "title": "New Movie",
            "description": "New description",
            "duration": 120,
            "genres": [self.genre.id],
            "actors": [self.actor.id],
        }
        res = self.client.post(url, payload)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_movie_admin(self):
        url = reverse("cinema:movie-list")
        self.client.force_authenticate(self.admin_user)
        payload = {
            "title": "New Movie",
            "description": "New description",
            "duration": 120,
            "genres": [self.genre.id],
            "actors": [self.actor.id],
        }
        res = self.client.post(url, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(title="New Movie")
        self.assertEqual(movie.description, "New description")

    def test_filter_movies_by_title(self):
        movie2 = sample_movie(title="Another Movie")
        url = reverse("cinema:movie-list")
        res = self.client.get(url, {"title": "Sample"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], "Sample movie")

    def test_filter_movies_by_genres(self):
        genre2 = sample_genre(name="Action")
        movie2 = sample_movie(title="Action Movie")
        movie2.genres.add(genre2)
        url = reverse("cinema:movie-list")
        res = self.client.get(url, {"genres": f"{genre2.id}"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], "Action Movie")

    def test_filter_movies_by_actors(self):
        actor2 = sample_actor(first_name="Brad", last_name="Pitt")
        movie2 = sample_movie(title="Brad Pitt Movie")
        movie2.actors.add(actor2)
        url = reverse("cinema:movie-list")
        res = self.client.get(url, {"actors": f"{actor2.id}"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], "Brad Pitt Movie")

    def test_upload_image_to_movie_admin(self):
        url = image_upload_url(self.movie.id)
        self.client.force_authenticate(self.admin_user)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(url, {"image": ntf}, format="multipart")
        self.movie.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)
        self.assertTrue(os.path.exists(self.movie.image.path))

    def test_upload_invalid_image(self):
        url = image_upload_url(self.movie.id)
        self.client.force_authenticate(self.admin_user)
        res = self.client.post(url, {"image": "not image"}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_movie_with_jwt_authentication(self):
        refresh = RefreshToken.for_user(self.user)
        access_token = refresh.access_token
        url = reverse("cinema:movie-list")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)

    def tearDown(self):
        if hasattr(self, "movie") and self.movie.image:
            self.movie.image.delete()
