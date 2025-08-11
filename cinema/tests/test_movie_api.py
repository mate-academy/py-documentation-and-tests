import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

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


class UnAuthenticatedUserToMovie(TestCase):

    def setUp(self) -> None:
        self.client = APIClient()

    def test_trying_to_get_any_information(self):
        res = self.client.get(reverse("cinema:movie-list"))
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        res = self.client.get(reverse("cinema:movie-detail", args=["1"]))
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


def create_movie(data):
    return Movie.objects.create(**data)


class AuthenticatedUserToMovie(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@gmail.com",
            password="test123",
        )
        self.client.force_authenticate(self.user)

    def test_list_view(self):
        genre = Genre.objects.create(name="movie")
        movie1 = {
            "title": "Test1",
            "duration": "2",
        }
        movie2 = {
            "title": "Test2",
            "duration": "2",
        }
        movie1 = create_movie(movie1)
        movie2 = create_movie(movie2)
        movie1.genres.set([genre])
        movie2.genres.set([genre])
        res = self.client.get(reverse("cinema:movie-list"))
        serializer = MovieListSerializer([movie1, movie2], many=True)
        self.assertEqual(res.data, serializer.data)

    def test_retrieve_movie(self):
        genre = Genre.objects.create(name="movie")
        movie1 = {
            "title": "Test1",
            "duration": "2",
        }
        movie1 = create_movie(movie1)
        movie1.genres.set([genre])
        res = self.client.get(reverse("cinema:movie-detail", args=["1"]))
        serializer = MovieDetailSerializer(movie1)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie(self):

        res = self.client.post(reverse("cinema:movie-list"), {
            "title": "Test1",
            "duration": "2",
        })
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminUserToMovie(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@gmail.com",
            "test123",
            is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        Genre.objects.create(name="movie")
        Actor.objects.create(first_name="leo", last_name="ant")
        payload = {
            "title": "Test1",
            "description": "ad",
            "duration": "2",
            "genres": [1, ],
            "actors": [1, ]
        }
        res = self.client.post(reverse("cinema:movie-list"), payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(Movie.objects.all()), 1)
        self.assertEqual(Movie.objects.get(id=1).title, "Test1")
