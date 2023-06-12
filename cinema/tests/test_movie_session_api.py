from django.contrib.auth import get_user_model
from django.db.models import Count, F
from django.test import TestCase
from django.urls import reverse_lazy, reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall
from cinema.serializers import (
    MovieSessionListSerializer,
    MovieSessionDetailSerializer
)

MOVIE_SESSION_URL = reverse("cinema:moviesession-list")


def detail_url(movie_session_id: int):
    return reverse_lazy("cinema:moviesession-detail", args=[movie_session_id])


def test_movie(**params) -> Movie:
    defaults = {
        "title": "Test movie",
        "description": "Description",
        "duration": 90
    }
    defaults.update(**params)
    return Movie.objects.create(**defaults)


def test_cinema_hall(**params) -> CinemaHall:
    return CinemaHall.objects.create(
        name="Test hall",
        rows=20,
        seats_in_row=20
    )


def test_movie_session(**params) -> MovieSession:
    defaults = {
        "show_time": "2023-06-01T13:00:00",
        "movie": test_movie(),
        "cinema_hall": test_cinema_hall()
    }
    defaults.update(**params)
    return MovieSession.objects.create(**defaults)


class UnauthenticatedMovieSessionApiTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self) -> None:
        response = self.client.get(MOVIE_SESSION_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieSessionApiTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@test.com",
            "Test1234",
        )
        self.client.force_authenticate(self.user)

    def test_list_movie_sessions(self) -> None:
        test_movie_session()
        test_movie_session(show_time="2023-07-01 13:00:00")
        movie_sessions = MovieSession.objects.all().annotate(
            tickets_available=(
                F("cinema_hall__rows") * F("cinema_hall__seats_in_row")
                - Count("tickets")
            )
        )
        serializer = MovieSessionListSerializer(movie_sessions, many=True)

        response = self.client.get(MOVIE_SESSION_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_filter_movie_session_by_time(self) -> None:
        test_movie_session(show_time="2023-06-01T13:00:00")
        test_movie_session(show_time="2023-07-01T13:00:00")
        annotated_moviesessions = MovieSession.objects.annotate(
            tickets_available=(
                    F("cinema_hall__rows") * F("cinema_hall__seats_in_row")
                    - Count("tickets")
            )
        )
        serializer1 = MovieSessionListSerializer(annotated_moviesessions[0])
        serializer2 = MovieSessionListSerializer(annotated_moviesessions[1])

        response = self.client.get(MOVIE_SESSION_URL, {"date": "2023-06-01"})

        self.assertIn(serializer1.data, response.data)
        self.assertNotIn(serializer2.data, response.data)

    def test_filter_movie_session_by_movie_id(self) -> None:
        movie1 = test_movie(title="Test movie 1")
        test_movie_session(movie=movie1)
        test_movie_session()
        annotated_moviesessions = MovieSession.objects.annotate(
            tickets_available=(
                    F("cinema_hall__rows") * F("cinema_hall__seats_in_row")
                    - Count("tickets")
            )
        )
        serializer1 = MovieSessionListSerializer(annotated_moviesessions[0])
        serializer2 = MovieSessionListSerializer(annotated_moviesessions[1])

        response = self.client.get(MOVIE_SESSION_URL, {"movie": f"{movie1.id}"})

        self.assertIn(serializer1.data, response.data)
        self.assertNotIn(serializer2.data, response.data)

    def test_retrieve_movie_session(self) -> None:
        movie_session = test_movie_session()
        url = detail_url(movie_session.id)
        serializer = MovieSessionDetailSerializer(movie_session)

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_create_movie_session_forbidden(self) -> None:
        payload = {
            "show_time": "2023-06-01T13:00:00",
            "movie": test_movie(),
            "cinema_hall": test_cinema_hall()
        }
        response = self.client.post(MOVIE_SESSION_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieSessionApiTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@admin.com",
            "test1234",
            is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_movie_session(self) -> None:
        movie = test_movie()
        cinema_hall = test_cinema_hall()
        payload = {
            "show_time": "2023-08-01T13:00:00",
            "movie": movie.id,
            "cinema_hall": cinema_hall.id
        }

        response = self.client.post(MOVIE_SESSION_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
