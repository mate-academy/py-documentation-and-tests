from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, CinemaHall, MovieSession

MOVIE_SESSION_URL = reverse("cinema:moviesession-list")


class UnauthenticatedMovieSessionApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(MOVIE_SESSION_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieSessionApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@test.com",
            "test_password"
        )
        self.client.force_authenticate(self.user)

        # create movie
        self.movie = Movie.objects.create(
            title="test_title",
            description="test_description",
            duration=120,
        )

        # create cinema_hall
        self.cinema_hall_ = CinemaHall.objects.create(
            name="test_name",
            rows=999,
            seats_in_row=999
        )

    def sample_movie_session__(self, **params):
        defaults = {
            "show_time": "2023-06-30T15:30:00Z",
            "movie": self.movie,
            "cinema_hall": self.cinema_hall_
        }
        defaults.update(**params)

        return MovieSession.objects.create(**defaults)

    def test_filter_movie_sessions(self):
        response = self.client.get(MOVIE_SESSION_URL, {"movie": "1"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
