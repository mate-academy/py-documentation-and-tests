import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor
from django.core.cache import cache

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
        cache.clear()

        self.client = APIClient()

        self.admin = get_user_model().objects.create_superuser(
            email="admin@cinema.test",
            password="TestPassword123!",
        )

        self.user = get_user_model().objects.create_user(
            email="user@cinema.test",
            password="TestPassword123!",
        )

        self.client.force_authenticate(user=self.admin)

        self.genre = sample_genre(name="Action")
        self.actor = sample_actor(
            first_name="Tom",
            last_name="Hanks",
        )

        self.movie = sample_movie(title="Avatar")
        self.movie.genres.add(self.genre)
        self.movie.actors.add(self.actor)

    def test_retrieve_movies(self):
        """Test retrieving a list of movies."""
        sample_movie(title="Titanic")

        response = self.client.get(MOVIE_URL)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(len(response.data), 2)

        titles = [movie["title"] for movie in response.data]

        self.assertIn("Avatar", titles)
        self.assertIn("Titanic", titles)

    def test_retrieve_movie_detail(self):
        """Test retrieving a single movie."""
        url = detail_url(self.movie.id)

        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(response.data["id"], self.movie.id)
        self.assertEqual(response.data["title"], "Avatar")

    def test_retrieve_nonexistent_movie(self):
        """Test retrieving a movie that does not exist."""
        url = detail_url(99999)

        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_filter_movies_by_title(self):
        """Test filtering movies by title."""
        sample_movie(title="Titanic")

        response = self.client.get(
            MOVIE_URL,
            {"title": "ava"},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Avatar")

    def test_filter_movies_by_genres(self):
        """Test filtering movies by genre IDs."""
        second_genre = sample_genre(name="Comedy")

        second_movie = sample_movie(title="Comedy movie")
        second_movie.genres.add(second_genre)

        response = self.client.get(
            MOVIE_URL,
            {"genres": str(self.genre.id)},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.movie.id)

    def test_filter_movies_by_actors(self):
        """Test filtering movies by actor IDs."""
        second_actor = sample_actor(
            first_name="Leonardo",
            last_name="DiCaprio",
        )

        second_movie = sample_movie(title="Second movie")
        second_movie.actors.add(second_actor)

        response = self.client.get(
            MOVIE_URL,
            {"actors": str(self.actor.id)},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.movie.id)

    def test_filter_movies_by_multiple_genres(self):
        """Test filtering movies using multiple genre IDs."""
        second_genre = sample_genre(name="Drama")

        second_movie = sample_movie(title="Drama movie")
        second_movie.genres.add(second_genre)

        genre_ids = f"{self.genre.id},{second_genre.id}"

        response = self.client.get(
            MOVIE_URL,
            {"genres": genre_ids},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(len(response.data), 2)

    def test_filter_movies_by_multiple_actors(self):
        """Test filtering movies using multiple actor IDs."""
        second_actor = sample_actor(
            first_name="Brad",
            last_name="Pitt",
        )

        second_movie = sample_movie(title="Second movie")
        second_movie.actors.add(second_actor)

        actor_ids = f"{self.actor.id},{second_actor.id}"

        response = self.client.get(
            MOVIE_URL,
            {"actors": actor_ids},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(len(response.data), 2)

    def test_create_movie_as_admin(self):
        """Test that admin can create movies."""
        payload = {
            "title": "New movie",
            "description": "Movie description",
            "duration": 120,
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
        self.assertTrue(
            Movie.objects.filter(title="New movie").exists()
        )

    def test_create_movie_invalid_data(self):
        """Test creating a movie with missing title."""
        payload = {
            "description": "Movie description",
            "duration": 120,
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

    def test_create_movie_as_regular_user(self):
        """Test that regular users cannot create movies."""
        self.client.force_authenticate(user=self.user)

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
                title="Forbidden movie"
            ).exists()
        )

    def test_create_movie_as_anonymous_user(self):
        """Test that anonymous users cannot create movies."""
        self.client.force_authenticate(user=None)

        payload = {
            "title": "Anonymous movie",
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

        self.assertIn(
            response.status_code,
            [
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            ],
        )

    def test_regular_user_can_view_movies(self):
        """Test that authenticated users can view movies."""
        self.client.force_authenticate(user=self.user)

        response = self.client.get(MOVIE_URL)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_regular_user_can_view_movie_detail(self):
        """Test that authenticated users can view movie details."""
        self.client.force_authenticate(user=self.user)

        response = self.client.get(detail_url(self.movie.id))

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_anonymous_user_cannot_view_movies(self):
        """Test that anonymous users cannot view movies."""
        self.client.force_authenticate(user=None)

        response = self.client.get(MOVIE_URL)

        self.assertIn(
            response.status_code,
            [
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            ],
        )

    def test_regular_user_cannot_upload_image(self):
        """Test that regular users cannot upload movie images."""
        self.client.force_authenticate(user=self.user)

        url = image_upload_url(self.movie.id)

        response = self.client.post(
            url,
            {"image": "invalid image"},
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_anonymous_user_cannot_upload_image(self):
        """Test that anonymous users cannot upload movie images."""
        self.client.force_authenticate(user=None)

        url = image_upload_url(self.movie.id)

        response = self.client.post(
            url,
            {"image": "invalid image"},
            format="multipart",
        )

        self.assertIn(
            response.status_code,
            [
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            ],
        )
