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
        "show_time": "2022-06-02 14:00:00",
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


class MovieImageUploadTests(TestCase):
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
        self.assertIn("image", res.data)
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

        self.assertIn("image", res.data)

    def test_image_url_is_shown_on_movie_list(self):
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(MOVIE_URL)

        self.assertIn("image", res.data[0].keys())

    def test_image_url_is_shown_on_movie_session_detail(self):
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(MOVIE_SESSION_URL)

        self.assertIn("movie_image", res.data[0].keys())


class MovieViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.user = get_user_model().objects.create_user(
            email="user@test.com",
            password="password",
        )

        self.admin = get_user_model().objects.create_superuser(
            email="admin@test.com",
            password="password",
        )

        self.genre = sample_genre()
        self.genre_action = sample_genre(name="Action")

        self.actor = sample_actor()
        self.actor_second = sample_actor(
            first_name="Brad",
            last_name="Pitt",
        )

        self.movie = sample_movie(title="The Matrix")
        self.movie.genres.add(self.genre)
        self.movie.actors.add(self.actor)

        self.other_movie = sample_movie(
            title="The Godfather",
            description="Crime movie",
        )
        self.other_movie.genres.add(self.genre_action)
        self.other_movie.actors.add(self.actor_second)

    def test_list_movies(self):
        self.client.force_authenticate(self.user)

        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)

    def test_retrieve_movie(self):
        self.client.force_authenticate(self.user)

        res = self.client.get(detail_url(self.movie.id))

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], self.movie.id)
        self.assertEqual(res.data["title"], self.movie.title)

    def test_filter_movies_by_title(self):
        self.client.force_authenticate(self.user)

        res = self.client.get(
            MOVIE_URL,
            {"title": "matrix"},
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], "The Matrix")

    def test_filter_movies_by_genres(self):
        self.client.force_authenticate(self.user)

        res = self.client.get(
            MOVIE_URL,
            {"genres": str(self.genre.id)},
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], "The Matrix")

    def test_filter_movies_by_actors(self):
        self.client.force_authenticate(self.user)

        res = self.client.get(
            MOVIE_URL,
            {"actors": str(self.actor.id)},
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], "The Matrix")

    def test_filter_movies_by_multiple_genres(self):
        self.client.force_authenticate(self.user)

        res = self.client.get(
            MOVIE_URL,
            {
                "genres": (
                    f"{self.genre.id},{self.genre_action.id}"
                )
            },
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)

    def test_filter_movies_by_multiple_actors(self):
        self.client.force_authenticate(self.user)

        res = self.client.get(
            MOVIE_URL,
            {
                "actors": (
                    f"{self.actor.id},{self.actor_second.id}"
                )
            },
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)

    def test_create_movie_as_admin(self):
        self.client.force_authenticate(self.admin)

        payload = {
            "title": "New Movie",
            "description": "New description",
            "duration": 120,
            "genres": [self.genre.id],
            "actors": [self.actor.id],
        }

        res = self.client.post(
            MOVIE_URL,
            payload,
            format="json",
        )

        self.assertEqual(
            res.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertTrue(
            Movie.objects.filter(title="New Movie").exists()
        )

    def test_create_movie_as_regular_user(self):
        self.client.force_authenticate(self.user)

        payload = {
            "title": "New Movie",
            "description": "New description",
            "duration": 120,
            "genres": [self.genre.id],
            "actors": [self.actor.id],
        }

        res = self.client.post(
            MOVIE_URL,
            payload,
            format="json",
        )

        self.assertEqual(
            res.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_create_movie_unauthenticated(self):
        res = self.client.post(
            MOVIE_URL,
            {},
            format="json",
        )

        self.assertEqual(
            res.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_list_movies_unauthenticated(self):
        res = self.client.get(MOVIE_URL)

        self.assertEqual(
            res.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_movie_list_uses_list_serializer(self):
        self.client.force_authenticate(self.user)

        res = self.client.get(MOVIE_URL)

        self.assertIn("genres", res.data[0])
        self.assertIn("actors", res.data[0])

    def test_movie_detail_uses_detail_serializer(self):
        self.client.force_authenticate(self.user)

        res = self.client.get(detail_url(self.movie.id))

        self.assertIsInstance(res.data["genres"], list)
        self.assertIsInstance(res.data["actors"], list)
