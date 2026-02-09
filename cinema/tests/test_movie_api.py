import os
import tempfile
from datetime import datetime

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import Actor, CinemaHall, Genre, Movie, MovieSession

MOVIE_URL = reverse("cinema:movie-list")
MOVIE_SESSION_URL = reverse("cinema:moviesession-list")


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


def image_upload_url(movie_id):
    return reverse("cinema:movie-upload-image", args=[movie_id])


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


def sample_movie_session(movie, **params):
    cinema_hall = CinemaHall.objects.create(name="Blue", rows=20, seats_in_row=20)  # noqa 501
    defaults = {
        "show_time": datetime(2022, 6, 2, 14, 0, 0),
        "movie": movie,
        "cinema_hall": cinema_hall,
    }
    defaults.update(params)
    return MovieSession.objects.create(**defaults)


class MovieImageUploadTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = get_user_model().objects.create_superuser(
            email="admin@myproject.com",
            password="password",
        )
        self.client.force_authenticate(self.admin)

        self.movie = sample_movie()
        self.genre = sample_genre()
        self.actor = sample_actor()

        self.movie.genres.add(self.genre)
        self.movie.actors.add(self.actor)

        self.movie_session = sample_movie_session(movie=self.movie)

    def tearDown(self):
        if self.movie.image:
            self.movie.image.delete()

    def test_upload_image_to_movie(self):
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

    def test_upload_image_bad_request(self):
        url = image_upload_url(self.movie.id)
        res = self.client.post(url, {"image": "not image"}, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_image_to_movie_list_does_not_set_image(self):
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)

            payload = {
                "title": "Title",
                "description": "Description",
                "duration": 90,
                "genres": [self.genre.id],
                "actors": [self.actor.id],
                "image": ntf,
            }
            res = self.client.post(MOVIE_URL, payload, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(title="Title")
        self.assertFalse(movie.image)

    def test_image_url_is_shown_on_movie_detail(self):
        # upload image
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")

        res = self.client.get(detail_url(self.movie.id))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)

    def test_image_url_is_shown_on_movie_list(self):
        # upload image
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")

        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data[0].keys())

    def test_movie_image_is_shown_on_movie_session_list(self):
        # upload image
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")

        res = self.client.get(MOVIE_SESSION_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("movie_image", res.data[0].keys())


class MovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user@test.com",
            password="pass12345",
        )
        self.client.force_authenticate(self.user)

        self.movie1 = sample_movie(title="The Ring")
        self.movie2 = sample_movie(title="Interstellar")

        self.genre1 = sample_genre(name="Drama")
        self.genre2 = sample_genre(name="Action")

        self.actor1 = sample_actor(first_name="Tom", last_name="Hardy")
        self.actor2 = sample_actor(first_name="Brad", last_name="Pitt")

        self.movie1.genres.add(self.genre1)
        self.movie1.actors.add(self.actor1)

        self.movie2.genres.add(self.genre2)
        self.movie2.actors.add(self.actor2)

    def test_list_movies(self):
        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(len(res.data) >= 2)

    def test_retrieve_movie_detail(self):
        res = self.client.get(detail_url(self.movie1.id))

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], self.movie1.id)

    def test_filter_movies_by_title(self):
        res = self.client.get(MOVIE_URL, {"title": "ring"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ids = [item["id"] for item in res.data]
        self.assertIn(self.movie1.id, ids)
        self.assertNotIn(self.movie2.id, ids)

    def test_filter_movies_by_genres(self):
        res = self.client.get(MOVIE_URL, {"genres": str(self.genre1.id)})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ids = [item["id"] for item in res.data]
        self.assertIn(self.movie1.id, ids)
        self.assertNotIn(self.movie2.id, ids)

    def test_filter_movies_by_actors(self):
        res = self.client.get(MOVIE_URL, {"actors": str(self.actor2.id)})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ids = [item["id"] for item in res.data]
        self.assertIn(self.movie2.id, ids)
        self.assertNotIn(self.movie1.id, ids)


class MovieCreatePermissionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.genre = sample_genre()
        self.actor = sample_actor()

        self.user = get_user_model().objects.create_user(
            email="user@test.com",
            password="pass12345",
        )
        self.admin = get_user_model().objects.create_superuser(
            email="admin@test.com",
            password="pass12345",
        )

    def test_create_movie_unauthorized(self):
        payload = {
            "title": "New",
            "description": "Desc",
            "duration": 100,
            "genres": [self.genre.id],
            "actors": [self.actor.id],
        }
        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_movie_forbidden_for_regular_user(self):
        self.client.force_authenticate(self.user)
        payload = {
            "title": "New",
            "description": "Desc",
            "duration": 100,
            "genres": [self.genre.id],
            "actors": [self.actor.id],
        }
        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_movie_allowed_for_admin(self):
        self.client.force_authenticate(self.admin)
        payload = {
            "title": "New",
            "description": "Desc",
            "duration": 100,
            "genres": [self.genre.id],
            "actors": [self.actor.id],
        }
        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Movie.objects.filter(title="New").exists())


class MovieUnauthenticatedReadOnlyTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.movie = sample_movie()

    def test_movie_list_allowed(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_movie_detail_allowed(self):
        res = self.client.get(detail_url(self.movie.id))
        self.assertEqual(res.status_code, status.HTTP_200_OK)


class MovieUploadImagePermissionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.movie = sample_movie()
        self.user = get_user_model().objects.create_user(
            email="user@test.com",
            password="pass12345",
        )

    def test_upload_image_unauthorized_returns_401(self):
        url = image_upload_url(self.movie.id)

        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)

            res = self.client.post(url, {"image": ntf}, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_upload_image_non_admin_returns_403(self):
        self.client.force_authenticate(self.user)
        url = image_upload_url(self.movie.id)

        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)

            res = self.client.post(url, {"image": ntf}, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
