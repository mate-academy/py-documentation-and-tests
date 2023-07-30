from datetime import datetime

import pytz
from django.contrib.auth import get_user_model
from django.db.models import Count, F
from django.test import TestCase
from django.urls import reverse, reverse_lazy
from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import Movie, CinemaHall, MovieSession
from cinema.serializers import MovieSessionListSerializer, MovieSessionDetailSerializer

MOVIE_SESSION_URL = reverse("cinema:moviesession-list")


# helper for creating url for movie_session detail
def detail_url(movie_session_id: int):
    return reverse("cinema:moviesession-detail", args=[movie_session_id])


# create MS sample for tests
def sample_movie(**params):
    defaults = {
        "title": "test",
        "description": "test",
        "duration": 100,
    }
    defaults.update(**params)

    return Movie.objects.create(**defaults)


def sample_cinema_hall(**params):
    defaults = {
        "name": "test",
        "rows": 10,
        "seats_in_row": 10,
    }
    defaults.update(**params)

    return CinemaHall.objects.create(**defaults)


def sample_movie_session(**params):
    defaults = {
        "movie": sample_movie(),
        "cinema_hall": sample_cinema_hall(),
        "show_time": "2023-06-30T15:30:00Z",
    }
    defaults.update(**params)

    return MovieSession.objects.create(**defaults)


class UnauthenticatedMovieSessionApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(MOVIE_SESSION_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class IsAuthenticated(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@test.com",
            "test1234",
        )
        self.client.force_authenticate(self.user)

    def test_list_ms(self):
        sample_movie_session()

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
        response = self.client.get(MOVIE_SESSION_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_filtering(self):

        # create movies and movie_sessions for filtering
        movie_1 = sample_movie(title="test1")
        movie_2 = sample_movie(title="test2")
        sample_movie_session(movie=movie_1)
        sample_movie_session(movie=movie_2)
        sample_movie_session(show_time="2023-10-30T15:30:00Z")

        # movie-session list with field tickets_available
        movie_sessions = MovieSession.objects.annotate(
            tickets_available=(
                F("cinema_hall__rows") * F("cinema_hall__seats_in_row")
                - Count("tickets")
            )
        )

        response1 = self.client.get(MOVIE_SESSION_URL, {"movie": f"{movie_1.id}"})
        response2 = self.client.get(MOVIE_SESSION_URL, {"date": "2023-10-30"})

        serializer1 = MovieSessionListSerializer(movie_sessions[0])
        serializer2 = MovieSessionListSerializer(movie_sessions[1])
        serializer3 = MovieSessionListSerializer(movie_sessions[2])

        self.assertIn(serializer1.data, response1.data)
        self.assertNotIn(serializer2.data, response1.data)
        self.assertIn(serializer3.data, response2.data)

    def test_retrieve(self) -> None:

        movie_session = sample_movie_session()

        url = detail_url(movie_session.id)

        response = self.client.get(url)

        serializer = MovieSessionDetailSerializer(movie_session)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_create_movie_session_forbidden(self) -> None:

        payload = {"show_time": "2023-06-01T13:00:00", "movie": sample_movie()}
        response = self.client.post(MOVIE_SESSION_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieSessionTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@test.com", "test1234", is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_moviesession(self) -> None:

        movie = sample_movie()
        cinema_hall = sample_cinema_hall()

        payload = {
            "show_time": datetime.fromisoformat("2023-06-01 13:00:00").replace(tzinfo=pytz.UTC),
            "movie": movie.id,
            "cinema_hall": cinema_hall.id,
        }

        response = self.client.post(MOVIE_SESSION_URL, payload)
        movie_session = MovieSession.objects.get(id=response.data["id"])

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # for key in payload:
        #     self.assertEqual(payload[key], getattr(movie_session, key))
