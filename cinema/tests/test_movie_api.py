import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor

MOVIE_URL = reverse("cinema:movie-list")
MOVIE_SESSION_URL = reverse("cinema:moviesession-list")


def sample_movie(**params):
    defaults = {
        "title": "Sample movie",
        "description": "Sample description",
        "duration": 90,
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)


def sample_genre(**params):
    defaults = {
        "name": "Drama",
    }
    defaults.update(params)
    return Genre.objects.create(**defaults)


def sample_actor(**params):
    defaults = {"first_name": "George", "last_name": "Clooney"}
    defaults.update(params)
    return Actor.objects.create(**defaults)


def sample_movie_session(**params):
    cinema_hall = CinemaHall.objects.create(
        name="Blue", rows=20, seats_in_row=20
    )

    defaults = {
        "show_time": "2026-06-02 14:00:00",
        "movie": None,
        "cinema_hall": cinema_hall,
    }
    defaults.update(params)

    return MovieSession.objects.create(**defaults)


def image_upload_url(movie_id):
    """Return URL for movie image upload"""
    return reverse("cinema:movie-upload-image", args=[movie_id])


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


class MovieUnauthenticatedApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class MovieAuthenticatedApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user@test.com", password="password123"
        )
        self.admin = get_user_model().objects.create_superuser(
            email="admin.user@cinema.com", password="1qazcde3"
        )

    def test_list_movies(self):
        self.client.force_authenticate(self.user)
        sample_movie(title="Movie 1")
        sample_movie(title="Movie 2")

        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)

    def test_retrieve_movie_detail(self):
        self.client.force_authenticate(self.user)
        movie = sample_movie(title="Test Movie")

        res = self.client.get(detail_url(movie.id))

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["title"], movie.title)

    def test_filter_movie_by_title(self):
        self.client.force_authenticate(self.user)
        mov1 = sample_movie(title="Matrix")
        sample_movie(title="Avatar")
        res = self.client.get(MOVIE_URL, {"title": "Matrix"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], mov1.title)

    def test_filter_movie_by_genres(self):
        self.client.force_authenticate(self.user)
        genre1 = sample_genre(name="Action")
        mov1 = sample_movie(title="Action Movie")
        mov2 = sample_movie(title="Comedy Movie")
        mov1.genres.add(genre1)

        res = self.client.get(MOVIE_URL, {"genres": f"{genre1.id}"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], mov1.title)

    def test_filter_movie_by_actors(self):
        self.client.force_authenticate(self.user)
        actor1 = sample_actor(first_name="Brad", last_name="Pitt")
        mov1 = sample_movie(title="Brad Movie")
        mov2 = sample_movie(title="Other Movie")
        mov1.actors.add(actor1)

        res = self.client.get(MOVIE_URL, {"actors": f"{actor1.id}"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], mov1.title)

    def test_create_movie_forbidden_for_regular_user(self):
        self.client.force_authenticate(self.user)
        payload = {
            "title": "Movie",
            "description": "Movie description",
            "duration": 90,
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_movie_allowed_for_admin(self):
        self.client.force_authenticate(self.admin)
        movie = sample_movie(title="Old Title")
        genre = sample_genre(name="Action")
        actor = sample_actor(first_name="Brad", last_name="Pitt")

        payload = {
            "title": "New Title",
            "description": "Updated description",
            "duration": 120,
            "genres": [genre.id],
            "actors": [actor.id],
        }
        res = self.client.put(detail_url(movie.id), payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        movie.refresh_from_db()
        self.assertEqual(movie.title, "New Title")

    def test_update_movie_allowed_for_admin(self):
        self.client.force_authenticate(self.admin)

        genre = sample_genre(name="Action")
        actor = sample_actor(first_name="Brad", last_name="Pitt")
        movie = sample_movie(title="Old Title")
        movie.genres.add(genre)
        movie.actors.add(actor)

        payload = {
            "title": "New Title",
            "description": "Updated description",
            "duration": 120,
            "genres": [genre.id],
            "actors": [actor.id],
        }
        res = self.client.put(detail_url(movie.id), payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        movie.refresh_from_db()
        self.assertEqual(movie.title, "New Title")

    def test_delete_movie_allowed_for_admin(self):
        self.client.force_authenticate(self.admin)
        movie = sample_movie(title="To Delete")
        res = self.client.delete(detail_url(movie.id))
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Movie.objects.filter(id=movie.id).exists())

    def test_upload_image_to_movie(self):
        self.client.force_authenticate(self.admin)
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
