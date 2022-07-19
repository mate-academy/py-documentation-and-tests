from datetime import datetime, timezone

from django.contrib.auth import get_user_model
from django.db.models import Count, F
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import CinemaHall, Movie, MovieSession
from cinema.serializers import MovieSessionSerializer, \
    MovieSessionListSerializer

MOVIE_SESSION_URL = reverse("cinema:moviesession-list")


def sample_cinema_hall(**params):
    defaults = {
        "name": "Blue",
        "rows": 20,
        "seats_in_row": 20
    }
    defaults.update(params)

    return CinemaHall.objects.create(**defaults)


def sample_movie(**params):
    defaults = {
        "title": "Sample movie",
        "description": "Sample description",
        "duration": 90,
    }
    defaults.update(params)

    return Movie.objects.create(**defaults)


def sample_movie_session(**params):
    cinema_hall = sample_cinema_hall()
    movie = sample_movie()
    defaults = {
        "show_time": datetime.now(),
        "movie": movie,
        "cinema_hall": cinema_hall,
    }
    defaults.update(params)

    return MovieSession.objects.create(**defaults)


class UnauthenticatedBusApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_SESSION_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedBusApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@test.com",
            "test12345"
        )
        self.client.force_authenticate(self.user)

    def test_list_movie_sessions(self):
        sample_movie_session()
        sample_movie_session()

        response = self.client.get(MOVIE_SESSION_URL)
        movie_sessions = (
            MovieSession.objects.all()
            .select_related("movie", "cinema_hall")
            .annotate(
                tickets_available=(
                        F("cinema_hall__rows")
                        * F("cinema_hall__seats_in_row")
                        - Count("tickets")
                )
            )
        )
        serializer = MovieSessionListSerializer(movie_sessions, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_filter_movie_sessions_by_movie(self):
        movie_1 = sample_movie(title="title 1")
        movie_2 = sample_movie(title="title 2")
        movie_3 = sample_movie(title="title 3")

        sample_movie_session(movie=movie_1)
        sample_movie_session(movie=movie_1)
        sample_movie_session(movie=movie_2)
        sample_movie_session(movie=movie_3)

        for movie in (movie_1, movie_2):
            response = self.client.get(
                MOVIE_SESSION_URL,
                {"movie": f"{movie.id}"}
            )
            for movie_session in response.data:
                self.assertTrue(movie.title, movie_session["movie_title"])

    def test_filter_movie_sessions_by_multiple_movies(self):
        movie_1 = sample_movie(title="title 1")
        movie_2 = sample_movie(title="title 2")
        movie_3 = sample_movie(title="title 3")

        sample_movie_session(movie=movie_1)
        sample_movie_session(movie=movie_1)
        sample_movie_session(movie=movie_2)
        sample_movie_session(movie=movie_3)

        response = self.client.get(
            MOVIE_SESSION_URL,
            {"movie": f"{movie_1.id},{movie_2.id}"}
        )
        for movie_session in response.data:
            self.assertIn(
                movie_session["movie_title"],
                (movie_1.title, movie_2.title)
            )

    def test_filter_movie_sessions_by_date(self):
        filter_date = datetime(2022, 1, 1)

        sample_movie_session(show_time=filter_date)
        sample_movie_session(show_time=filter_date)
        sample_movie_session(show_time="2022-02-02 05:00:00")
        sample_movie_session()
        sample_movie_session()

        response = self.client.get(
            MOVIE_SESSION_URL,
            {"date": filter_date.strftime("%Y-%m-%d")}
        )

        for movie_session in response.data:
            session_date = datetime.strptime(
                movie_session["show_time"], "%Y-%m-%dT%H:%M:%S%z"
            )

            self.assertEqual(session_date.date(), filter_date.date())
