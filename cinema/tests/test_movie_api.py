import os
import tempfile
from datetime import datetime

from PIL import Image

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import (
    Actor,
    CinemaHall,
    Genre,
    Movie,
    MovieSession,
)


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
    defaults = {
        "first_name": "George",
        "last_name": "Clooney",
    }
    defaults.update(params)

    return Actor.objects.create(**defaults)


def sample_movie_session(**params):
    cinema_hall = CinemaHall.objects.create(
        name="Blue",
        rows=20,
        seats_in_row=20,
    )

    defaults = {
        "show_time": datetime(2022, 6, 2, 14, 0),
        "movie": None,
        "cinema_hall": cinema_hall,
    }
    defaults.update(params)

    return MovieSession.objects.create(**defaults)


def image_upload_url(movie_id):
    """Return URL for uploading an image to a movie."""
    return reverse(
        "cinema:movie-upload-image",
        args=[movie_id],
    )


def detail_url(movie_id):
    """Return URL for movie detail."""
    return reverse(
        "cinema:movie-detail",
        args=[movie_id],
    )


class MovieImageUploadTests(TestCase):
    def setUp(self):
        cache.clear()

        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            email="admin@myproject.com",
            password="password",
        )
        self.client.force_authenticate(self.user)

        self.movie = sample_movie()
        self.genre = sample_genre()
        self.actor = sample_actor()
        self.movie_session = sample_movie_session(
            movie=self.movie,
        )

    def tearDown(self):
        for movie in Movie.objects.all():
            if movie.image:
                movie.image.delete(save=False)

    def test_upload_image_to_movie(self):
        """Test uploading an image to a movie."""
        url = image_upload_url(self.movie.id)

        with tempfile.NamedTemporaryFile(suffix=".jpg") as image_file:
            image = Image.new("RGB", (10, 10))
            image.save(image_file, format="JPEG")
            image_file.seek(0)

            response = self.client.post(
                url,
                {"image": image_file},
                format="multipart",
            )

        self.movie.refresh_from_db()

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertIn("image", response.data)
        self.assertTrue(
            os.path.exists(self.movie.image.path)
        )

    def test_upload_image_bad_request(self):
        """Test uploading an invalid image."""
        url = image_upload_url(self.movie.id)

        response = self.client.post(
            url,
            {"image": "not image"},
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_post_image_to_movie_list(self):
        with tempfile.NamedTemporaryFile(suffix=".jpg") as image_file:
            image = Image.new("RGB", (10, 10))
            image.save(image_file, format="JPEG")
            image_file.seek(0)

            response = self.client.post(
                MOVIE_URL,
                {
                    "title": "Title",
                    "description": "Description",
                    "duration": 90,
                    "genres": [self.genre.id],
                    "actors": [self.actor.id],
                    "image": image_file,
                },
                format="multipart",
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        movie = Movie.objects.get(title="Title")

        self.assertFalse(movie.image)

    def test_image_url_is_shown_on_movie_detail(self):
        url = image_upload_url(self.movie.id)

        with tempfile.NamedTemporaryFile(suffix=".jpg") as image_file:
            image = Image.new("RGB", (10, 10))
            image.save(image_file, format="JPEG")
            image_file.seek(0)

            self.client.post(
                url,
                {"image": image_file},
                format="multipart",
            )

        response = self.client.get(
            detail_url(self.movie.id)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertIn("image", response.data)

    def test_image_url_is_shown_on_movie_list(self):
        url = image_upload_url(self.movie.id)

        with tempfile.NamedTemporaryFile(suffix=".jpg") as image_file:
            image = Image.new("RGB", (10, 10))
            image.save(image_file, format="JPEG")
            image_file.seek(0)

            self.client.post(
                url,
                {"image": image_file},
                format="multipart",
            )

        response = self.client.get(MOVIE_URL)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertIn(
            "image",
            response.data[0],
        )

    def test_image_url_is_shown_on_movie_session_list(self):
        url = image_upload_url(self.movie.id)

        with tempfile.NamedTemporaryFile(suffix=".jpg") as image_file:
            image = Image.new("RGB", (10, 10))
            image.save(image_file, format="JPEG")
            image_file.seek(0)

            self.client.post(
                url,
                {"image": image_file},
                format="multipart",
            )

        response = self.client.get(MOVIE_SESSION_URL)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertIn(
            "movie_image",
            response.data[0],
        )


class PublicMovieApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()

    def test_authentication_required(self):
        response = self.client.get(MOVIE_URL)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )


class PrivateMovieApiTests(TestCase):
    def setUp(self):
        cache.clear()

        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user@example.com",
            password="testpass123",
        )
        self.client.force_authenticate(self.user)

        self.genre = sample_genre(name="Action")
        self.actor = sample_actor(
            first_name="John",
            last_name="Smith",
        )

        self.movie = sample_movie(
            title="Example movie",
            description="Example description",
            duration=120,
        )
        self.movie.genres.add(self.genre)
        self.movie.actors.add(self.actor)

    def test_list_movies(self):
        response = self.client.get(MOVIE_URL)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["title"],
            self.movie.title,
        )

    def test_retrieve_movie_detail(self):
        response = self.client.get(
            detail_url(self.movie.id)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data["id"],
            self.movie.id,
        )
        self.assertEqual(
            response.data["title"],
            self.movie.title,
        )
        self.assertEqual(
            response.data["description"],
            self.movie.description,
        )
        self.assertEqual(
            response.data["duration"],
            self.movie.duration,
        )
        self.assertIn("genres", response.data)
        self.assertIn("actors", response.data)

    def test_retrieve_missing_movie(self):
        response = self.client.get(
            detail_url(999999)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_filter_movies_by_title(self):
        sample_movie(
            title="Completely different film"
        )

        response = self.client.get(
            MOVIE_URL,
            {"title": "Example"},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        titles = [
            movie["title"]
            for movie in response.data
        ]

        self.assertIn(
            self.movie.title,
            titles,
        )
        self.assertNotIn(
            "Completely different film",
            titles,
        )

    def test_filter_movies_by_genres(self):
        comedy = sample_genre(name="Comedy")

        comedy_movie = sample_movie(
            title="Comedy movie"
        )
        comedy_movie.genres.add(comedy)

        response = self.client.get(
            MOVIE_URL,
            {"genres": str(self.genre.id)},
        )

        titles = [
            movie["title"]
            for movie in response.data
        ]

        self.assertIn(
            self.movie.title,
            titles,
        )
        self.assertNotIn(
            comedy_movie.title,
            titles,
        )

    def test_filter_movies_by_multiple_genres(self):
        comedy = sample_genre(name="Comedy")
        horror = sample_genre(name="Horror")

        comedy_movie = sample_movie(
            title="Comedy movie"
        )
        comedy_movie.genres.add(comedy)

        horror_movie = sample_movie(
            title="Horror movie"
        )
        horror_movie.genres.add(horror)

        response = self.client.get(
            MOVIE_URL,
            {
                "genres": (
                    f"{comedy.id},{horror.id}"
                )
            },
        )

        titles = [
            movie["title"]
            for movie in response.data
        ]

        self.assertIn(
            comedy_movie.title,
            titles,
        )
        self.assertIn(
            horror_movie.title,
            titles,
        )
        self.assertNotIn(
            self.movie.title,
            titles,
        )

    def test_filter_movies_by_actors(self):
        second_actor = sample_actor(
            first_name="Jane",
            last_name="Doe",
        )

        second_movie = sample_movie(
            title="Second movie"
        )
        second_movie.actors.add(second_actor)

        response = self.client.get(
            MOVIE_URL,
            {"actors": str(self.actor.id)},
        )

        titles = [
            movie["title"]
            for movie in response.data
        ]

        self.assertIn(
            self.movie.title,
            titles,
        )
        self.assertNotIn(
            second_movie.title,
            titles,
        )

    def test_filter_movies_by_multiple_actors(self):
        second_actor = sample_actor(
            first_name="Jane",
            last_name="Doe",
        )
        third_actor = sample_actor(
            first_name="Bruce",
            last_name="Wayne",
        )

        second_movie = sample_movie(
            title="Second movie"
        )
        second_movie.actors.add(second_actor)

        third_movie = sample_movie(
            title="Third movie"
        )
        third_movie.actors.add(third_actor)

        response = self.client.get(
            MOVIE_URL,
            {
                "actors": (
                    f"{second_actor.id},"
                    f"{third_actor.id}"
                )
            },
        )

        titles = [
            movie["title"]
            for movie in response.data
        ]

        self.assertIn(
            second_movie.title,
            titles,
        )
        self.assertIn(
            third_movie.title,
            titles,
        )
        self.assertNotIn(
            self.movie.title,
            titles,
        )

    def test_regular_user_cannot_create_movie(self):
        payload = {
            "title": "Forbidden movie",
            "description": "Description",
            "duration": 100,
            "genres": [self.genre.id],
            "actors": [self.actor.id],
        }

        response = self.client.post(
            MOVIE_URL,
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertFalse(
            Movie.objects.filter(
                title="Forbidden movie",
            ).exists()
        )

    def test_regular_user_cannot_upload_image(self):
        response = self.client.post(
            image_upload_url(self.movie.id),
            {},
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )


class AdminMovieApiTests(TestCase):
    def setUp(self):
        cache.clear()

        self.client = APIClient()
        self.admin = get_user_model().objects.create_superuser(
            email="admin@example.com",
            password="testpass123",
        )
        self.client.force_authenticate(self.admin)

        self.genre = sample_genre(name="Fantasy")
        self.actor = sample_actor(
            first_name="Robert",
            last_name="Downey",
        )

    def test_admin_can_create_movie(self):
        payload = {
            "title": "New movie",
            "description": "New movie description",
            "duration": 110,
            "genres": [self.genre.id],
            "actors": [self.actor.id],
        }

        response = self.client.post(
            MOVIE_URL,
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        movie = Movie.objects.get(
            title=payload["title"]
        )

        self.assertEqual(
            movie.description,
            payload["description"],
        )
        self.assertEqual(
            movie.duration,
            payload["duration"],
        )
        self.assertTrue(
            movie.genres.filter(
                id=self.genre.id
            ).exists()
        )
        self.assertTrue(
            movie.actors.filter(
                id=self.actor.id
            ).exists()
        )

    def test_create_movie_with_invalid_payload(self):
        payload = {
            "title": "",
            "description": "Description",
            "duration": 100,
            "genres": [self.genre.id],
            "actors": [self.actor.id],
        }

        response = self.client.post(
            MOVIE_URL,
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertFalse(
            Movie.objects.filter(
                description="Description",
            ).exists()
        )
