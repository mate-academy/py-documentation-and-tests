from datetime import datetime

from django.utils import timezone
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall
from cinema.serializers import MovieSessionListSerializer, MovieSessionDetailSerializer

MOVIE_SESSION_URL = reverse("cinema:moviesession-list")


def sample_movie(**params):
    defaults = {
        "title": "Sample movie",
        "description": "Sample description",
        "duration": 90,
    }
    defaults.update(params)

    return Movie.objects.create(**defaults)


def sample_cinema_hall(**params):
    defaults = {"name": "Main Hall", "rows": 15, "seats_in_row": 20}
    defaults.update(params)
    return CinemaHall.objects.create(**defaults)


def sample_movie_session(**params):
    defaults = {
        "show_time": timezone.make_aware(datetime(2025, 6, 2, 14, 0, 0)),
        "movie": sample_movie(),
        "cinema_hall": sample_cinema_hall(),
    }
    defaults.update(params)
    return MovieSession.objects.create(**defaults)


class UnauthenticatedMovieSessionAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_SESSION_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieSessionAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.test", password="testpassword"
        )
        self.client.force_authenticate(self.user)

    def test_auth_required(self):
        res = self.client.get(MOVIE_SESSION_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_movie_sessions_list(self):
        sample_movie_session()

        res = self.client.get(MOVIE_SESSION_URL)
        sessions = MovieSession.objects.all()
        self.assertTrue(sessions.exists(), "No MovieSession objects found!")

        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_filter_movie_sessions_by_movie_id(self):
        session_without_movie = sample_movie_session()
        movie = sample_movie(title="Filtered Movie")
        session_with_movie = sample_movie_session(movie=movie)

        res = self.client.get(MOVIE_SESSION_URL, {"movie": f"{movie.id}"})

        serializer_without_movie = MovieSessionListSerializer(session_without_movie)
        serializer_with_movie = MovieSessionListSerializer(session_with_movie)

        self.assertIn(serializer_with_movie.data | {"tickets_available": 300}, res.data)
        self.assertNotIn(serializer_without_movie.data, res.data)

    def test_filter_movie_sessions_by_date(self):
        session_old = sample_movie_session(
            show_time=timezone.make_aware(datetime(2025, 6, 1, 14, 0, 0))
        )
        session_new = sample_movie_session(
            show_time=timezone.make_aware(datetime(2025, 6, 3, 14, 0, 0))
        )

        res = self.client.get(MOVIE_SESSION_URL, {"date": "2025-06-03"})

        serializer_old = MovieSessionListSerializer(session_old)
        serializer_new = MovieSessionListSerializer(session_new)

        self.assertIn(serializer_new.data | {"tickets_available": 300}, res.data)
        self.assertNotIn(serializer_old.data, res.data)

    def test_retrieve_movie_session_detail(self):
        session = sample_movie_session()

        url = reverse("cinema:moviesession-detail", args=[session.id])
        res = self.client.get(url)

        serializer = MovieSessionDetailSerializer(session)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_session_forbidden(self):
        movie = sample_movie()
        cinema_hall = sample_cinema_hall()
        payload = {
            "show_time": "2025-06-02 14:00:00",
            "movie": movie.id,
            "cinema_hall": cinema_hall.id,
        }

        res = self.client.post(MOVIE_SESSION_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieSessionTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@admin.test", password="testpassword", is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_movie_session_create(self):
        movie = sample_movie()
        cinema_hall = sample_cinema_hall()

        payload = {
            "show_time": "2025-06-02 14:00:00",
            "movie": movie.id,
            "cinema_hall": cinema_hall.id,
        }

        res = self.client.post(MOVIE_SESSION_URL, payload)
        session = MovieSession.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        for key in ["show_time"]:
            self.assertEqual(
                timezone.make_naive(session.show_time).strftime("%Y-%m-%d %H:%M:%S"),
                payload[key],
            )

        self.assertEqual(session.movie.id, payload["movie"])
        self.assertEqual(session.cinema_hall.id, payload["cinema_hall"])

    def test_movie_session_delete_forbidden(self):
        session = sample_movie_session()

        url = reverse("cinema:moviesession-detail", args=[session.id])
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
