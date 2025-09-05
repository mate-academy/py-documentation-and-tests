import tempfile
import os
import json
import yaml
from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.settings import api_settings
from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor
from unittest import skip


class TestMovieViewSetCore(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "user2@myproject.com", "password"
        )
        self.admin = get_user_model().objects.create_superuser(
            "admin2@myproject.com", "password"
        )
        self.genre = sample_genre(name="Drama")
        self.actor = sample_actor(first_name="Jane", last_name="Doe")
        self.movie = sample_movie(
            title="Test Movie", genres=[self.genre], actors=[self.actor]
        )

    def authenticate(self, user=None):
        if user is None:
            user = self.user
        self.client.force_authenticate(user)

    def get_jwt_token(self, user=None):
        if user is None:
            user = self.user
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)

    def test_retrieve_movie_detail(self):
        self.authenticate()
        url = reverse("cinema:movie-detail", args=[self.movie.id])
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["id"], self.movie.id)

    def test_create_movie_admin_only(self):
        # Unauthenticated
        data = {
            "title": "New Movie",
            "description": "desc",
            "duration": 120,
            "genres": [self.genre.id],
            "actors": [self.actor.id],
        }
        res = self.client.post(MOVIE_URL, data)
        self.assertEqual(res.status_code, 401)
        # Authenticated, not admin
        self.authenticate(self.user)
        res = self.client.post(MOVIE_URL, data)
        self.assertEqual(res.status_code, 403)
        # Admin
        self.authenticate(self.admin)
        res = self.client.post(MOVIE_URL, data)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()["title"], "New Movie")

    def test_update_movie_admin_only(self):
        url = reverse("cinema:movie-detail", args=[self.movie.id])
        patch_data = {"title": "Updated Title"}
        # Unauthenticated
        res = self.client.patch(url, patch_data)
        self.assertEqual(res.status_code, 401)
        # Authenticated, not admin
        self.authenticate(self.user)
        res = self.client.patch(url, patch_data)
        self.assertEqual(res.status_code, 403)
        # Admin
        self.authenticate(self.admin)
        res = self.client.patch(url, patch_data)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["title"], "Updated Title")

    def test_delete_movie_admin_only(self):
        url = reverse("cinema:movie-detail", args=[self.movie.id])
        # Unauthenticated
        res = self.client.delete(url)
        self.assertEqual(res.status_code, 401)
        # Authenticated, not admin
        self.authenticate(self.user)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, 403)
        # Admin
        self.authenticate(self.admin)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, 204)
        self.assertFalse(Movie.objects.filter(id=self.movie.id).exists())

    @skip(
        "DRF test client does not enforce throttling; "
        "test only in integration or with real cache."
    )
    @override_settings(
        REST_FRAMEWORK={
            "DEFAULT_THROTTLE_CLASSES": [
                "rest_framework.throttling.UserRateThrottle",
                "rest_framework.throttling.AnonRateThrottle",
            ],
            "DEFAULT_THROTTLE_RATES": {"user": "2/minute", "anon": "2/minute"},
        }
    )
    def test_throttling(self):
        # Authenticated user
        self.authenticate(self.user)
        for _ in range(2):
            res = self.client.get(MOVIE_URL)
            self.assertNotEqual(res.status_code, 429)
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, 429)

        self.client.logout()
        for _ in range(2):
            res = self.client.get(MOVIE_URL)
            self.assertNotEqual(res.status_code, 429)
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, 429)


class TestMovieOpenAPISchema(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = get_user_model().objects.create_superuser(
            "admin3@myproject.com", "password"
        )
        self.client.force_authenticate(self.admin)

    def test_movie_list_schema_has_filter_params(self):
        res = self.client.get("/api/schema/")
        self.assertEqual(res.status_code, 200)
        schema = yaml.safe_load(res.content)
        # Find /api/cinema/movies/ GET operation
        paths = schema.get("paths", {})
        movie_list = None
        for path, ops in paths.items():
            if path.endswith("/api/cinema/movies/") and "get" in ops:
                movie_list = ops["get"]
                break
        self.assertIsNotNone(movie_list)
        params = {p["name"]: p for p in movie_list.get("parameters", [])}
        self.assertIn("title", params)
        self.assertIn("genres", params)
        self.assertIn("actors", params)
        self.assertEqual(params["title"]["in"], "query")
        self.assertEqual(params["genres"]["in"], "query")
        self.assertEqual(params["actors"]["in"], "query")


class TestMovieViewSetFilter(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "user@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)
        self.genre1 = sample_genre(name="Action")
        self.genre2 = sample_genre(name="Comedy")
        self.actor1 = sample_actor(first_name="Tom", last_name="Hanks")
        self.actor2 = sample_actor(first_name="Brad", last_name="Pitt")
        self.movie1 = sample_movie(
            title="Funny Movie", genres=[self.genre2], actors=[self.actor1]
        )
        self.movie2 = sample_movie(
            title="Action Movie", genres=[self.genre1], actors=[self.actor2]
        )

    def test_filter_movies_by_title(self):
        res = self.client.get(MOVIE_URL, {"title": "Funny"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["title"], "Funny Movie")

    def test_filter_movies_by_genres(self):
        res = self.client.get(MOVIE_URL, {"genres": str(self.genre1.id)})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["title"], "Action Movie")
        self.assertEqual(data[0]["title"], "Action Movie")

    def test_filter_movies_by_actors(self):
        res = self.client.get(MOVIE_URL, {"actors": str(self.actor2.id)})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["title"], "Action Movie")

    def test_filter_movies_by_multiple_actors(self):
        ids = f"{self.actor1.id},{self.actor2.id}"
        res = self.client.get(MOVIE_URL, {"actors": ids})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()
        self.assertEqual(len(data), 2)
        self.assertEqual(len(res.json()), 2)

    def test_filter_movies_by_multiple_genres(self):
        ids = f"{self.genre1.id},{self.genre2.id}"
        res = self.client.get(MOVIE_URL, {"genres": ids})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)


MOVIE_URL = reverse("cinema:movie-list")
MOVIE_SESSION_URL = reverse("cinema:moviesession-list")


def sample_movie(**params):
    defaults = {
        "title": "Sample movie",
        "description": "Sample description",
        "duration": 90,
    }
    genres = params.pop("genres", None)
    actors = params.pop("actors", None)
    defaults.update(params)
    movie = Movie.objects.create(**defaults)
    if genres is not None:
        movie.genres.set(genres)
    if actors is not None:
        movie.actors.set(actors)
    return movie


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

    from django.utils import timezone
    import datetime

    defaults = {
        "show_time": timezone.make_aware(
            datetime.datetime(2022, 6, 2, 14, 0, 0)
        ),
        "movie": None,
        "cinema_hall": cinema_hall,
    }
    defaults.update(params)

    return MovieSession.objects.create(**defaults)


def image_upload_url(movie_id):
    """Return URL for recipe image upload"""
    return reverse("cinema:movie-upload-image", args=[movie_id])


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


class TestMovieImageUpload(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)
        self.movie = sample_movie()
        self.genre = sample_genre()
        self.actor = sample_actor()
        self.movie_session = sample_movie_session(movie=self.movie)

    def tearDown(self):
        self.movie.image.delete()

    def test_upload_image_to_movie(self):
        """Test uploading an image to movie"""
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(url, {"image": ntf}, format="multipart")
        self.movie.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.json())
        self.assertTrue(os.path.exists(self.movie.image.path))

    def test_upload_image_bad_request(self):
        """Test uploading an invalid image"""
        url = image_upload_url(self.movie.id)
        res = self.client.post(url, {"image": "not image"}, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_image_to_movie_list(self):
        url = MOVIE_URL
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(
                url,
                {
                    "title": "Title",
                    "description": "Description",
                    "duration": 90,
                    "genres": [1],
                    "actors": [1],
                    "image": ntf,
                },
                format="multipart",
            )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(title="Title")
        self.assertFalse(movie.image)

    def test_image_url_is_shown_on_movie_detail(self):
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(detail_url(self.movie.id))

        self.assertIn("image", res.json())

    def test_image_url_is_shown_on_movie_list(self):
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(MOVIE_URL)

        self.assertIn("image", res.json()[0].keys())

    def test_image_url_is_shown_on_movie_session_detail(self):
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(MOVIE_SESSION_URL)

        data = res.json()
        self.assertIn("movie_image", data[0].keys())
