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


class UnauthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com",
            password="testpass123",
        )
        self.client.force_authenticate(self.user)

    def test_list_movies(self):
        sample_movie()
        sample_movie(title="Another Movie")
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)

    def test_filter_by_title(self):
        movie1 = sample_movie(title="Interstellar")
        sample_movie(title="Inception")
        res = self.client.get(MOVIE_URL, {"title": "inter"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], movie1.title)

    def test_filter_by_genres(self):
        genre = Genre.objects.create(name="Action")
        movie_with_genre = sample_movie(title="Action Movie")
        movie_with_genre.genres.add(genre)
        sample_movie(title="Drama Movie")
        res = self.client.get(MOVIE_URL, {"genres": genre.id})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], movie_with_genre.title)

    def test_filter_by_actors(self):
        actor = Actor.objects.create(first_name="Tom", last_name="Hanks")
        movie_with_actor = sample_movie(title="Cast Away")
        movie_with_actor.actors.add(actor)
        sample_movie(title="No Actors Movie")
        res = self.client.get(MOVIE_URL, {"actors": actor.id})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], movie_with_actor.title)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        url = detail_url(movie.id)
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["title"], movie.title)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "New Movie",
            "description": "Some description",
            "duration": 90,
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = get_user_model().objects.create_superuser(
            email="admin@test.com",
            password="adminpass123",
        )
        self.client.force_authenticate(self.admin)

    def test_create_movie(self):
        payload = {
            "title": "New Movie",
            "description": "Great film",
            "duration": 100,
        }
        res = self.client.post(MOVIE_URL, payload, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, msg=f"Помилка від DRF: {res.data}")
        movie = Movie.objects.get(id=res.data["id"])
        self.assertEqual(movie.title, payload["title"])

    def test_create_movie_with_genres(self):
        genre = Genre.objects.create(name="Sci-Fi")
        payload = {
            "title": "Sci-Fi Movie",
            "description": "Space adventures",
            "duration": 130,
            "genres": [genre.id],
        }
        res = self.client.post(MOVIE_URL, payload, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, msg=f"Помилка від DRF: {res.data}")
        self.assertIn(genre.id, res.data["genres"])

    def test_create_movie_with_actors(self):
        actor = Actor.objects.create(
            first_name="Leonardo", last_name="DiCaprio"
        )
        payload = {
            "title": "Inception",
            "description": "Dream within a dream",
            "duration": 148,
            "actors": [actor.id],
        }
        res = self.client.post(MOVIE_URL, payload, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, msg=f"Помилка від DRF: {res.data}")
        self.assertIn(actor.id, res.data["actors"])
