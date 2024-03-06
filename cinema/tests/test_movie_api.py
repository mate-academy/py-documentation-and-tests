import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.db.models import F, Count
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor, Ticket, Order
from cinema.serializers import MovieSessionListSerializer, MovieSessionDetailSerializer

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


def movie_detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


def movie_session_detail_url(movie_session_id):
    return reverse("cinema:moviesession-detail", args=[movie_session_id])


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
        res = self.client.get(movie_detail_url(self.movie.id))

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


class UnauthenticatedMovieSessionApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(MOVIE_SESSION_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieSessionApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@test.com",
            "testpassword123"
        )
        self.client.force_authenticate(self.user)

    def test_list_movie_sessions(self):
        movie = sample_movie()
        movie_session = sample_movie_session(movie=movie)
        order = Order.objects.create(
            user=self.user
        )
        Ticket.objects.create(
            movie_session=movie_session,
            order=order,
            row=1,
            seat=1
        )
        res = self.client.get(MOVIE_SESSION_URL)

        movie_sessions = (
            MovieSession.objects.all()
            .select_related("movie", "cinema_hall")
            .annotate(
                tickets_available=(
                        F("cinema_hall__rows") * F("cinema_hall__seats_in_row")
                        - Count("tickets")
                )
            )
        )
        serializer = MovieSessionListSerializer(movie_sessions, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_movie_session_with_date_queryparams(self):
        blank_movie = sample_movie()
        blank_movie_session = sample_movie_session(movie=blank_movie)
        movie1 = sample_movie(title="movie1")
        sample_movie_session(movie=movie1, show_time="2023-10-10")
        movie2 = sample_movie(title="movie2")
        sample_movie_session(movie=movie2, show_time="2023-10-10")
        res = self.client.get(MOVIE_SESSION_URL, {"date": "2023-10-10"})

        movie_sessions = (
            MovieSession.objects.all()
            .select_related("movie", "cinema_hall")
            .annotate(
                tickets_available=(
                        F("cinema_hall__rows") * F("cinema_hall__seats_in_row")
                        - Count("tickets")
                )
            )
        )
        movie_sessions = movie_sessions.filter(show_time__date="2023-10-10")
        blank_serializer = MovieSessionListSerializer(blank_movie_session)
        serializer = MovieSessionListSerializer(movie_sessions, many=True)

        self.assertNotIn(blank_serializer.data, res.data)
        self.assertEqual(serializer.data, res.data)

    def test_movie_session_with_movie_queryparams(self):
        blank_movie = sample_movie()
        blank_movie_session = sample_movie_session(movie=blank_movie)
        movie1 = sample_movie(title="test1")
        sample_movie_session(movie=movie1)

        res = self.client.get(MOVIE_SESSION_URL, {"movie": f"{movie1.id}"})

        movie_sessions = (
            MovieSession.objects.all()
            .select_related("movie", "cinema_hall")
            .annotate(
                tickets_available=(
                        F("cinema_hall__rows") * F("cinema_hall__seats_in_row")
                        - Count("tickets")
                )
            ).filter(movie_id=movie1.id)
        )
        blank_serializer = MovieSessionListSerializer(blank_movie_session)
        serializer = MovieSessionListSerializer(movie_sessions, many=True)

        self.assertNotIn(blank_serializer.data, res.data)
        self.assertEqual(serializer.data, res.data)

    def test_retrieve_movie_session_detail(self):
        movie1 = sample_movie(title="test1")
        sample_movie_session(movie=movie1)

        movie_session = MovieSession.objects.first()

        url = movie_session_detail_url(movie_session.id)

        res = self.client.get(url)

        serializer = MovieSessionDetailSerializer(movie_session)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_session_forbidden(self):
        movie = sample_movie()
        cinema_hall = CinemaHall.objects.create(
            name="test cinema_hall",
            rows=5,
            seats_in_row=12
        )
        payload = {
            "show_time": "2024-10-10",
            "movie": movie,
            "cinema_hall": cinema_hall
        }

        res = self.client.post(MOVIE_SESSION_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieSessionApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@admin.com",
            "testpassword123",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)

    def test_create_movie_session(self):
        movie = sample_movie()
        cinema_hall = CinemaHall.objects.create(
            name="test cinema_hall",
            rows=5,
            seats_in_row=12
        )
        payload = {
            "show_time": "2024-10-10",
            "movie": movie.id,
            "cinema_hall": cinema_hall.id
        }

        res = self.client.post(MOVIE_SESSION_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
