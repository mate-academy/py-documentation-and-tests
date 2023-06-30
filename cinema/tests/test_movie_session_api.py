from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, CinemaHall, MovieSession
from cinema.serializers import MovieSessionSerializer, MovieSessionListSerializer

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

    def test_list_movie_sessions(self):
        # self.sample_movie_session()
        sample_session = self.sample_movie_session__()

        response = self.client.get(MOVIE_SESSION_URL)

        movie_sessions = MovieSession.objects.all()
        cinema_halls = CinemaHall.objects.all()
        serializer = MovieSessionListSerializer(
            movie_sessions, many=True
        )

        # Delete data about available tickets "tickets_available"
        # since this data is only available through the MovieSessionViewSet
        # and not via the serializer itself.
        response.data[0].pop("tickets_available")

        hall_name_response = response.data[0]["cinema_hall_name"]
        hall_name_serizlizer = serializer.data[0]["cinema_hall_name"]

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # self.assertEqual(
        #     response.data,
        #     serializer.data
        # )

        hall_name_response = response.data[0]["cinema_hall_name"]
        hall_name_serizlizer = serializer.data[0]["cinema_hall_name"]

        self.assertEqual(
            response.data[0]["cinema_hall_name"],
            serializer.data[0]["cinema_hall_name"]
        )
