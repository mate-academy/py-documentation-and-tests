from datetime import datetime, time

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from rest_framework.test import APIClient

from cinema.models import MovieSession, Movie, CinemaHall
from cinema.serializers import (
    MovieSessionListSerializer,
    MovieSessionDetailSerializer,
)

MOVIE_SESSION_URL = reverse("cinema:movie_session-list")


def data_converter(data: str):
    dt = datetime.strptime(data, "%Y-%m-%d")
    return datetime.combine(dt, time.min).isoformat()


def detail_url(movie_session_id: int):
    return reverse("cinema:movie_session-detail", args=[movie_session_id])


def sample_movie_sessions(**params):
    defaults = {
        "show_time": data_converter("2024-10-08"),
        "movie": Movie.objects.create(
            title="Movie", description="Test", duration=100
        ),
        "cinema_hall": CinemaHall.objects.create(
            name="TestHall", rows=10, seats_in_row=20
        ),
    }
    defaults.update(params)

    return MovieSession.objects.create(**defaults)


class UnauthenticatedMovieSessionApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_SESSION_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieSessionApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com", password="test12345"
        )
        self.client.force_authenticate(self.user)

    def test_filter_movie_session_by_date(self):
        movie_session_one = sample_movie_sessions()
        movie_session_two = sample_movie_sessions()
        test_date = "2024-10-09"
        movie_session_two.show_time = data_converter(test_date)
        movie_session_two.tickets_available = 200
        movie_session_two.save()

        res = self.client.get(
            MOVIE_SESSION_URL, {"date": f"{test_date}", "movie": 2}
        )

        serialize1 = MovieSessionListSerializer(movie_session_one)
        serialize2 = MovieSessionListSerializer(movie_session_two)

        self.assertNotIn(serialize1.data, res.data)
        self.assertIn(serialize2.data, res.data)

    def test_retrieve_movie_session_detail(self):
        movie_session = sample_movie_sessions()

        url = detail_url(movie_session.id)
        res = self.client.get(url)

        serializer = MovieSessionDetailSerializer(movie_session)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_session_forbidden(self):
        payload = {
            "show_time": data_converter("2024-10-08"),
            "movie": Movie.objects.create(
                title="Movie", description="Test", duration=100
            ),
            "cinema_hall": CinemaHall.objects.create(
                name="TestHall", rows=10, seats_in_row=20
            ),
        }
        res = self.client.post(MOVIE_SESSION_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieSessionApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@admin.com",
            password="admin12345",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)

    def test_create_movie_session(self):
        sample_movie_sessions()
        payload = {
            "show_time": datetime.strptime("2024-10-08", "%Y-%m-%d"),
            "movie": 1,
            "cinema_hall": 1,
        }
        res = self.client.post(MOVIE_SESSION_URL, payload)
        movie_session = MovieSession.objects.get(id=res.data["id"])
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        payload["movie"] = Movie.objects.get(id=1)
        payload["cinema_hall"] = CinemaHall.objects.get(id=1)

        for key in payload:
            self.assertEqual(payload[key], getattr(movie_session, key))
