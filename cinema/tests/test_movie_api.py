import tempfile
import os
from faker import Faker
import random

from PIL import Image
from django.contrib.auth import get_user_model
from django.db.models import F, Count
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.serializers import (
    MovieSessionListSerializer,
    MovieListSerializer,
    MovieDetailSerializer
)

from cinema.models import (
    Movie,
    MovieSession,
    CinemaHall,
    Genre,
    Actor,
    Order,
    Ticket,
)

MOVIE_URL = reverse("cinema:movie-list")
MOVIE_SESSION_URL = reverse("cinema:moviesession-list")


class Fake:
    @staticmethod
    def title():
        return Faker().catch_phrase()

    @staticmethod
    def description():
        return Faker().text()

    @staticmethod
    def duration():
        return random.randint(60, 180)

    @staticmethod
    def genre_name():
        return Faker().word()

    @staticmethod
    def first_name():
        return Faker().first_name()

    @staticmethod
    def last_name():
        return Faker().last_name()

    @staticmethod
    def email():
        return Faker().email()

    @staticmethod
    def password():
        return Faker().password()


def sample_movie(**params):
    defaults = {
        "title": Fake.title(),
        "description": Fake.description(),
        "duration": Fake.duration(),
    }
    defaults.update(params)

    return Movie.objects.create(**defaults)


def sample_genre(**params):
    defaults = {
        "name": Fake.genre_name(),
    }
    defaults.update(params)

    return Genre.objects.create(**defaults)


def sample_actor(**params):
    defaults = {
        "first_name": Fake.first_name(),
        "last_name": Fake.last_name(),
    }
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
            Fake.email(), Fake.password()
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
        """Test that authentication is required for accessing movie list."""

        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email=Fake.email(),
            password=Fake.password(),
        )
        self.client.force_authenticate(self.user)

    def test_movies_list(self) -> None:
        """Test that movies list is returned correctly."""

        movies = [sample_movie() for _ in range(3)]
        genres = [sample_genre() for _ in range(3)]
        actors = [sample_actor() for _ in range(3)]

        for movie, genre, actor in zip(movies, genres, actors):
            movie.genres.add(genre)
            movie.actors.add(actor)

        res = self.client.get(MOVIE_URL)

        serializer = MovieListSerializer(Movie.objects.all(), many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movie_by_genre(self) -> None:
        """Test filtering movies by genre."""

        movies = [sample_movie() for _ in range(3)]
        genres = [sample_genre() for _ in range(2)]

        for movie, genre in zip(movies[:2], genres):
            movie.genres.add(genre)

        movie_serializers = [MovieListSerializer(movie) for movie in movies]

        genre_ids = ",".join(str(genre.id) for genre in genres)
        res = self.client.get(MOVIE_URL, {"genres": genre_ids})

        for movie_serializer in movie_serializers[:2]:
            self.assertIn(movie_serializer.data, res.data)

        self.assertNotIn(movie_serializers[2].data, res.data)

    def test_filter_movie_by_actor(self) -> None:
        """Test filtering movies by actor."""

        movie_1 = sample_movie()
        movie_2 = sample_movie()

        actor = sample_actor()

        movie_1.actors.add(actor)

        res = self.client.get(
            MOVIE_URL,
            {"actors": f"{actor.id}"}
        )

        serializer_1 = MovieListSerializer(movie_1)
        serializer_3 = MovieListSerializer(movie_2)

        self.assertIn(serializer_1.data, res.data)
        self.assertNotIn(serializer_3.data, res.data)

    def test_filter_movie_by_title(self) -> None:
        """Test filtering movies by title."""

        movies = [sample_movie() for _ in range(5)]

        res = self.client.get(
            MOVIE_URL,
            {"title": str(movies[0].title)[:4]}
        )

        serializers = [MovieListSerializer(movie) for movie in movies]

        for serializer in serializers:
            if serializer.instance.title.startswith(str(movies[0].title)[:4]):
                self.assertIn(serializer.data, res.data)
            else:
                self.assertNotIn(serializer.data, res.data)

    def test_movie_detail(self) -> None:
        """Test retrieving details of a movie."""
        movie = sample_movie()
        genres = [sample_genre() for _ in range(3)]
        actors = [sample_actor() for _ in range(5)]

        for genre, actor in zip(genres, actors):
            movie.genres.add(genre)
            movie.actors.add(actor)

        url = detail_url(movie.id)

        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.data, serializer.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_create_movie_not_admin(self) -> None:
        """Test that a non-admin user cannot create a movie."""

        payload = {
            "title": Fake.title(),
            "description": Fake.description(),
            "duration": random.randint(60, 180),
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email=Fake.email(),
            password=Fake.password(),
            is_staff=True,
        )
        self.client.force_authenticate(self.user)

    def test_movie_create(self) -> None:
        actor = sample_actor()
        genre = sample_genre()

        payload = {
            "title": Fake.title(),
            "description": Fake.description(),
            "duration": Fake.duration(),
            "actors": actor.id,
            "genres": genre.id
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_delete_movie_not_allowed(self):
        """
        Test that delete a movie is not allowed.
        """

        movie = sample_movie()
        url = detail_url(movie.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_update_movie_not_allowed(self):
        """
        Test that updating a movie is not allowed.
        """

        movie = sample_movie()
        payload = {
            "title": Fake.title(),
            "description": Fake.description()
        }
        url = detail_url(movie.id)
        res = self.client.put(url, payload)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_update_movie_partially_not_allowed(self) -> None:
        """
        Test that partially updating a movie is not allowed.
        """

        movie = sample_movie()
        payload = {
            "title": Fake.title(),
        }
        url = detail_url(movie.id)
        res = self.client.patch(url, payload)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class AuthenticatedMovieSessionApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email=Fake.email(),
            password=Fake.password(),
        )
        self.client.force_authenticate(self.user)

    def test_movie_sessions_list(self) -> None:
        """Test retrieving a list of movie sessions."""

        movie = sample_movie()
        movie_session = sample_movie_session(movie=movie)
        order = Order.objects.create(
            user=self.user
        )
        Ticket.objects.create(
            movie_session=movie_session,
            order=order,
            row=1,
            seat=9
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
