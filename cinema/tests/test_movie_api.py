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

# Constants for superuser creation
ADMIN_EMAIL = "admin.user@cinema.com"
ADMIN_PASSWORD = "1qazcde3"

def create_admin_user():
    """Create and return a superuser for testing"""
    return get_user_model().objects.create_superuser(
        email=ADMIN_EMAIL,
        password=ADMIN_PASSWORD
    )

# Sample factories
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
    """Return URL for movie image upload"""
    return reverse("cinema:movie-upload-image", args=[movie_id])


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


class MovieImageUploadTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = create_admin_user()
        self.client.force_authenticate(self.user)
        self.movie = sample_movie()
        self.genre = sample_genre()
        self.actor = sample_actor()
        self.movie_session = sample_movie_session(movie=self.movie)

    def tearDown(self):
        if self.movie.image:
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
        """POST image via movie list endpoint"""
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
                    "genres": [self.genre.id],
                    "actors": [self.actor.id],
                    "image": ntf,
                },
                format="multipart",
            )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(title="Title")
        self.assertFalse(movie.image)  # image not saved in this endpoint

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
        self.user = create_admin_user()
        self.client.force_authenticate(self.user)
        self.genre = sample_genre()
        self.actor = sample_actor()

    def test_list_movies(self):
        movie = sample_movie()
        movie.genres.add(self.genre)
        movie.actors.add(self.actor)

        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)

    def test_retrieve_movie(self):
        movie = sample_movie()
        url = detail_url(movie.id)

        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], movie.id)

    def test_create_movie(self):
        payload = {
            "title": "New Movie",
            "description": "Test desc",
            "duration": 120,
            "genres": [self.genre.id],
            "actors": [self.actor.id],
        }

        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        res_data = res.data
        # Fix: genres and actors are returned as list of IDs
        self.assertEqual(res_data["title"], payload["title"])
        self.assertEqual(res_data["duration"], payload["duration"])
        self.assertCountEqual(res_data["genres"], payload["genres"])
        self.assertCountEqual(res_data["actors"], payload["actors"])
        self.assertEqual(Movie.objects.count(), 1)

    def test_update_movie(self):
        movie = sample_movie()
        url = detail_url(movie.id)
        payload = {
            "title": "Updated",
            "description": "Updated desc",
            "duration": 150,
            "genres": [self.genre.id],
            "actors": [self.actor.id],
        }

        res = self.client.put(url, payload)
        movie.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(movie.title, "Updated")

    def test_partial_update_movie(self):
        movie = sample_movie()
        url = detail_url(movie.id)
        res = self.client.patch(url, {"title": "Patched"})
        movie.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(movie.title, "Patched")

    def test_delete_movie(self):
        movie = sample_movie()
        url = detail_url(movie.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Movie.objects.filter(id=movie.id).exists())

    def test_filter_movies_by_title(self):
        sample_movie(title="Batman")
        sample_movie(title="Superman")
        res = self.client.get(MOVIE_URL, {"title": "Bat"})
        self.assertEqual(len(res.data), 1)

    def test_filter_movies_by_genre(self):
        genre2 = sample_genre(name="Comedy")
        movie1 = sample_movie(title="Movie 1")
        movie1.genres.add(self.genre)
        movie2 = sample_movie(title="Movie 2")
        movie2.genres.add(genre2)
        res = self.client.get(MOVIE_URL, {"genres": self.genre.id})
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["id"], movie1.id)

    def test_filter_movies_by_actor(self):
        actor2 = sample_actor(first_name="Brad", last_name="Pitt")
        movie1 = sample_movie(title="Movie 1")
        movie1.actors.add(self.actor)
        movie2 = sample_movie(title="Movie 2")
        movie2.actors.add(actor2)
        res = self.client.get(MOVIE_URL, {"actors": self.actor.id})
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["id"], movie1.id)

    def test_auth_required(self):
        """Test that authentication is required"""
        client = APIClient()
        res = client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
