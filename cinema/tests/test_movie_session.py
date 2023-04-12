# class UnAuthenticatedMovieSessionApiTests
# class AuthenticatedMovieSessionApiTests
# class AdminMovieSessionApiTests
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import CinemaHall, MovieSession, Movie, Genre, Actor
from cinema.serializers import (
    MovieSessionSerializer,
    MovieSessionListSerializer,
    MovieSessionDetailSerializer,
)

MOVIE_SESSION_URL = reverse("cinema:moviesession-list")


def detail_url(session_id: int):
    return reverse("cinema:moviesession-detail", args=[session_id])


def sample_movie(**params):
    defaults = {
        "title": "Sample movie",
        "description": "Sample description",
        "duration": 90,
    }
    defaults.update(params)

    return Movie.objects.create(**defaults)


def sample_movie_session(**params):
    cinema_hall = CinemaHall.objects.create(name="Blue", rows=20, seats_in_row=20)

    defaults = {
        "show_time": "2024-10-09T13:00:00Z",
        "movie": None,
        "cinema_hall": cinema_hall,
    }
    defaults.update(params)

    return MovieSession.objects.create(**defaults)


class UnAuthenticatedMovieSessionApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        result = self.client.get(MOVIE_SESSION_URL)
        self.assertEqual(result.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieSessionApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)

    def list_movie_sessions(self):
        movie = sample_movie(title="First_movie")
        sample_movie_session(movie=movie, show_time="2023-10-09T13:00:00Z")
        sample_movie_session(movie=movie)
        result = self.client.get(MOVIE_SESSION_URL)
        sessions = MovieSession.objects.all()
        serializer = MovieSessionListSerializer(sessions, many=True)
        self.assertEqual(result.status_code, status.HTTP_200_OK)
        self.assertEqual(result.data, serializer.data)

    def test_filter_session_by_movie(self):
        movie1 = sample_movie(title="First_movie")
        movie2 = sample_movie(title="Second_movie")
        movie_session1 = sample_movie_session(movie=movie1)
        movie_session2 = sample_movie_session(movie=movie2)
        serializer1 = MovieSessionListSerializer(movie_session1)
        serializer2 = MovieSessionListSerializer(movie_session2)
        result = self.client.get(MOVIE_SESSION_URL, {"movie": f"{movie1.id}"})
        self.assertEqual(len(result.data), 1)
        self.assertNotIn(serializer2.data, result.data)

    def test_filter_session_by_date(self):
        movie1 = sample_movie(title="First_movie")
        movie2 = sample_movie(title="Second_movie")
        movie_session1 = sample_movie_session(
            movie=movie1, show_time="2023-09-02T13:00:00Z"
        )
        movie_session2 = sample_movie_session(movie=movie2)
        serializer1 = MovieSessionListSerializer(movie_session1)
        serializer2 = MovieSessionListSerializer(movie_session2)
        result = self.client.get(MOVIE_SESSION_URL, {"date": "2023-09-02"})
        self.assertEqual(len(result.data), 1)
        self.assertNotIn(serializer2.data, result.data)

    def test_retrieve_movie_session_detail(self):
        movie1 = sample_movie(title="First_movie")
        movie_session1 = sample_movie_session(movie=movie1)
        url = detail_url(movie_session1.id)
        result = self.client.get(url)

        serializer = MovieSessionDetailSerializer(movie_session1)
        self.assertEqual(result.status_code, status.HTTP_200_OK)
        self.assertEqual(result.data, serializer.data)

    def test_create_movie_session_forbidden(self):
        sample_movie(title="First_movie")
        CinemaHall.objects.create(name="Blue", rows=20, seats_in_row=20)
        payload = {
            "show_time": "2024-10-08T13:00:00Z",
            "movie": 1,
            "cinema_hall": 1,
        }
        result = self.client.post(MOVIE_SESSION_URL, payload)
        self.assertEqual(result.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieSessionApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)

    def test_create_movie_session(self):
        sample_movie(title="First_movie")
        CinemaHall.objects.create(name="Blue", rows=20, seats_in_row=20)
        payload = {
            "show_time": "2024-10-08T13:00:00Z",
            "movie": 1,
            "cinema_hall": 1,
        }
        result = self.client.post(MOVIE_SESSION_URL, payload)
        self.assertEqual(result.status_code, status.HTTP_201_CREATED)
