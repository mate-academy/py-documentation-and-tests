import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor
from user.models import User

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
    cinema_hall = CinemaHall.objects.create(name="Blue", rows=20, seats_in_row=20)

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


class MovieViewSetTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.base_url = "/api/cinema/movies/"
        self.admin_user = User.objects.create_superuser(
            email="admin@test.com", password="adminpass"
        )
        self.regular_user = User.objects.create_user(
            password="testpass", email="test@test.com"
        )
        self.genre = Genre.objects.create(name="Action")
        self.actor = Actor.objects.create(first_name="John", last_name="Doe")
        self.movie = Movie.objects.create(
            title="Test Movie", description="Test Description", duration=120
        )
        self.movie.genres.add(self.genre)
        self.movie.actors.add(self.actor)
        self.genre_comedy = Genre.objects.create(name="Comedy")
        self.actor_comedy = Actor.objects.create(first_name="Jane", last_name="Doe")
        self.comedy_movie = Movie.objects.create(
            title="Comedy Movie", description="A funny movie", duration=90
        )
        self.comedy_movie.genres.add(self.genre_comedy)
        self.comedy_movie.actors.add(self.actor_comedy)

    def test_list_movies_regular_user(self):
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    def test_retrieve_movie_regular_user(self):
        self.client.force_authenticate(user=self.regular_user)
        url = f"{self.base_url}{self.movie.id}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["title"], "Test Movie")

    def test_unauthorized_access(self):
        self.client.logout()
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 401)

    def test_create_movie_regular_user(self):
        self.client.force_authenticate(user=self.admin_user)
        data = {
            "title": "New Movie",
            "description": "New movie description",
            "duration": 150,
        }
        response = self.client.post(self.base_url, data)
        self.assertEqual(response.status_code, 400)

    def test_create_movie_admin(self):
        self.client.force_authenticate(user=self.admin_user)

        genre = Genre.objects.create(name="Test Genre")
        actor = Actor.objects.create(first_name="John", last_name="Doe")

        data = {
            "title": "New Movie by Admin",
            "description": "New movie description by Admin",
            "duration": 150,
            "genres": [genre.id],
            "actors": [actor.id],
        }
        response = self.client.post(self.base_url, data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Movie.objects.count(), 3)

    def test_update_movie_regular_user(self):
        self.client.force_authenticate(user=self.admin_user)
        data = {
            "title": "Updated Movie",
            "description": "Updated description",
            "duration": 130,
        }
        url = f"{self.base_url}{self.movie.id}/"
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, 405)

    def test_update_movie_admin(self):
        self.client.force_authenticate(user=self.admin_user)
        data = {
            "title": "Updated Movie by Admin",
            "description": "Updated description by Admin",
            "duration": 130,
        }
        url = f"{self.base_url}{self.movie.id}/"
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, 405)

    def test_filter_movies_by_title(self):
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get(f"{self.base_url}?title=Comedy")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            any(movie["title"] == "Comedy Movie" for movie in response.data)
        )

    def test_filter_movies_by_genre(self):
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get(f"{self.base_url}?genres={self.genre_comedy.id}")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(any("Comedy" in movie["genres"] for movie in response.data))

    def test_filter_movies_by_actor(self):
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get(f"{self.base_url}?actors={self.actor_comedy.id}")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(any("Jane Doe" in movie["actors"] for movie in response.data))
