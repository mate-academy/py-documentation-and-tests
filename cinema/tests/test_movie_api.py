import tempfile
import os
from datetime import datetime

from PIL import Image
from django.contrib.auth import get_user_model
from django.db.models import F
from django.db.models.aggregates import Count
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor
from cinema.serializers import (
    MovieListSerializer,
    MovieSessionListSerializer
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


def sample_cinema_hall(**params):
    defaults = {"name": "Blue", "rows": 10, "seats_in_row": 10}
    defaults.update(params)
    return CinemaHall.objects.create(**defaults)


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
            email="user@test.com",
            password="testpass123",
        )
        self.client.force_authenticate(self.user)

    def test_list_movies_uses_list_serializer(self):
        movie1 = sample_movie(title="Movie A")
        movie2 = sample_movie(title="Movie B")

        genre1 = sample_genre(name="Action")
        genre2 = sample_genre(name="Sci-Fi")
        actor = sample_actor(first_name="Brad", last_name="Pitt")
        movie1.genres.add(genre1)
        movie1.actors.add(actor)

        movie2.genres.add(genre2)

        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        movies = Movie.objects.prefetch_related("genres", "actors")
        serializer = MovieListSerializer(movies, many=True)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movie_by_title(self):
        sample_movie(title="Sci-Fi Movie")
        sample_movie(title="Thriller Movie")
        sample_movie(title="Other Movie")
        query = "th"

        res = self.client.get(MOVIE_URL, {"title": query})
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        movies = Movie.objects.filter(title__icontains=query)
        serializer = MovieListSerializer(movies, many=True)
        self.assertEqual(serializer.data, res.data)

    def test_filter_by_multiple_genres(self):
        genre1 = sample_genre(name="Sci-Fi")
        genre2 = sample_genre(name="Thriller")

        movie1 = sample_movie(title="Sci-Fi Movie")
        movie2 = sample_movie(title="Thriller Movie")
        movie3 = sample_movie(title="Other Movie")

        movie1.genres.add(genre1)
        movie2.genres.add(genre2)

        res = self.client.get(MOVIE_URL, {"genres": f"{genre1.id},{genre2.id}"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ids = [m["id"] for m in res.data]
        self.assertIn(movie1.id, ids)
        self.assertIn(movie2.id, ids)
        self.assertNotIn(movie3.id, ids)

    def test_filter_by_multiple_actors(self):
        actor1 = sample_actor(first_name="Actor", last_name="One")
        actor2 = sample_actor(first_name="Actor", last_name="Two")

        movie1 = sample_movie(title="Movie One")
        movie2 = sample_movie(title="Movie Two")
        movie3 = sample_movie(title="Movie Three")

        movie1.actors.add(actor1)
        movie2.actors.add(actor2)

        res = self.client.get(MOVIE_URL, {"actors": f"{actor1.id},{actor2.id}"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        ids = [m["id"] for m in res.data]
        self.assertIn(movie1.id, ids)
        self.assertIn(movie2.id, ids)
        self.assertNotIn(movie3.id, ids)

    def test_create_movie_forbidden_for_regular_user(self):
        payload = {
            "title": "Unauthorized Movie",
            "description": "Should not be created",
            "duration": 90,
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Movie.objects.filter(title="Unauthorized Movie").exists())


class TestAuthenticatedMovieSessions(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="one@test.com",
            password="abctest123password",
        )
        self.client.force_authenticate(self.user)

    def test_filter_movie_session_by_movie_id(self):
        movie1 = sample_movie(title="Sci-Fi Movie")
        movie2 = sample_movie(title="Thriller Movie")
        cinema_hall = sample_cinema_hall()
        sample_movie_session(movie=movie1, cinema_hall=cinema_hall)
        sample_movie_session(movie=movie2, cinema_hall=cinema_hall)

        res = self.client.get(MOVIE_SESSION_URL, {"movie": movie1.id})
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        sessions = (
            MovieSession.objects.filter(movie_id=movie1.id)
            .select_related("movie", "cinema_hall")
            .annotate(
                tickets_available=(
                        F("cinema_hall__rows") * F("cinema_hall__seats_in_row")
                        - Count("tickets")
                )
            )
        )
        serializer = MovieSessionListSerializer(sessions, many=True)
        self.assertEqual(serializer.data, res.data)

    def test_filter_movie_session_by_date(self):
        movie = sample_movie()
        cinema_hall = sample_cinema_hall()

        session1 = sample_movie_session(
            movie=movie,
            cinema_hall=cinema_hall,
            show_time=datetime(2024, 6, 1, 14, 0)
        )
        session2 = sample_movie_session(
            movie=movie,
            cinema_hall=cinema_hall,
            show_time=datetime(2024, 7, 15, 18, 0)
        )

        res = self.client.get(MOVIE_SESSION_URL, {"date": "2024-06-01"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        ids = [s["id"] for s in res.data]
        self.assertIn(session1.id, ids)
        self.assertNotIn(session2.id, ids)


class AdminMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = get_user_model().objects.create_user(
            email="admin@test.com", password="adminpass123", is_staff=True
        )
        self.client.force_authenticate(self.admin)

    def test_create_movie_basic(self):
        payload = {
            "title": "Admin Movie",
            "description": "Created by admin",
            "duration": 100,
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(id=res.data["id"])

        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_create_movie_with_genres(self):
        genre1 = sample_genre(name="Action")
        genre2 = sample_genre(name="Drama")
        payload = {
            "title": "Movie with Genres",
            "description": "desc",
            "duration": 110,
            "genres": [genre1.id, genre2.id],
        }
        res = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=res.data["id"])
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        genres = movie.genres.all()

        self.assertIn(genre1, genres)
        self.assertIn(genre2, genres)
        self.assertEqual(genres.count(), 2)

    def test_create_movie_without_required_fields(self):
        payload = {
            "description": "desc",
            "duration": 110,
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
