import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient, APITestCase
from rest_framework import status
from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor
from cinema.serializers import (
    MovieListSerializer,
    MovieSessionDetailSerializer,
    MovieSessionSerializer
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


class UnauthenticatedMovieSessionApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_SESSION_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieSessionApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@email.com", password="testpass"
        )
        self.client.force_authenticate(self.user)
        self.movie = Movie.objects.create(
            title="Test Movie", description="Test Description", duration=100
        )

    def test_movie_session_list(self):
        """Test retrieving movie sessions"""
        session_1 = MovieSession.objects.create(movie=self.movie, show_time="2025-06-01T15:00:00")
        session_2 = MovieSession.objects.create(movie=self.movie, show_time="2025-06-01T18:00:00")

        res = self.client.get(MOVIE_SESSION_URL)

        sessions = MovieSession.objects.all()
        serializer = MovieSessionSerializer(sessions, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movie_sessions_by_movie(self):
        """Test filtering movie sessions by movie ID"""
        session_1 = MovieSession.objects.create(movie=self.movie, show_time="2025-06-01T15:00:00")
        movie_2 = Movie.objects.create(
            title="Another Movie", description="Another Description", duration=90
        )
        session_2 = MovieSession.objects.create(movie=movie_2, show_time="2025-06-01T18:00:00")

        res = self.client.get(MOVIE_SESSION_URL, {"movie": self.movie.id})

        serializer_session_1 = MovieSessionSerializer(session_1)
        serializer_session_2 = MovieSessionSerializer(session_2)

        self.assertIn(serializer_session_1.data, res.data)
        self.assertNotIn(serializer_session_2.data, res.data)

    def test_filter_movie_sessions_by_date(self):
        """Test filtering movie sessions by date"""
        session_1 = MovieSession.objects.create(movie=self.movie, show_time="2025-06-01T15:00:00")
        session_2 = MovieSession.objects.create(movie=self.movie, show_time="2025-06-02T18:00:00")

        res = self.client.get(MOVIE_SESSION_URL, {"date": "2025-06-01"})

        serializer_session_1 = MovieSessionSerializer(session_1)
        serializer_session_2 = MovieSessionSerializer(session_2)

        self.assertIn(serializer_session_1.data, res.data)
        self.assertNotIn(serializer_session_2.data, res.data)

    def test_retrieve_movie_session_detail(self):
        """Test retrieving a movie session detail"""
        session = MovieSession.objects.create(movie=self.movie, show_time="2025-06-01T15:00:00")

        url = reverse('movie-session-detail', args=[session.id])
        res = self.client.get(url)

        serializer = MovieSessionSerializer(session)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_session_forbidden(self):
        """Test creating a movie session without proper permissions (non-admin)"""
        payload = {
            "movie": self.movie.id,
            "show_time": "2025-06-01T15:00:00"
        }
        res = self.client.post(MOVIE_SESSION_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class UnauthenticatedMovieSessionApiTests(APITestCase):

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_SESSION_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieSessionApiTests(APITestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@email.com", password="testpass"
        )
        self.client.force_authenticate(self.user)

    def test_movie_list(self):
        sample_movie()
        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.data, serializer.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)


    def test_create_movie_session_forbidden(self):
        movie = sample_movie()
        cinema_hall = CinemaHall.objects.create(name="Hall 1", rows=10, seats_in_row=15)
        payload = {
            "movie": movie.id,
            "cinema_hall": cinema_hall.id,
            "show_time": "2025-06-01T15:00:00",
        }
        res = self.client.post(MOVIE_SESSION_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieSessionApiTests(APITestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@email.com",
            password="adminpass",
            is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_movie_session(self):
        movie = sample_movie()
        cinema_hall = CinemaHall.objects.create(name="Hall 1", rows=10, seats_in_row=15)
        payload = {
            "movie": movie.id,
            "cinema_hall": cinema_hall.id,
            "show_time": "2025-06-01T15:00:00",
        }
        res = self.client.post(MOVIE_SESSION_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        session = MovieSession.objects.get(id=res.data["id"])
        serializer = MovieSessionSerializer(session)
        self.assertEqual(res.data, serializer.data)