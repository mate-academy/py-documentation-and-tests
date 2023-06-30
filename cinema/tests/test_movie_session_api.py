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

    # def test_list_movie_sessions(self):
    #     self.sample_movie_session__()
    #
    #     response = self.client.get(MOVIE_SESSION_URL)
    #
    #     movie_sessions = MovieSession.objects.all()
    #     serializer = MovieSessionListSerializer(
    #         movie_sessions, many=True
    #     )
    #
    #     # Delete data about available tickets "tickets_available"
    #     # since this data is only available through the MovieSessionViewSet
    #     # and not via the serializer itself.
    #     response.data[0].pop("tickets_available")
    #
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)
    #     self.assertEqual(
    #         response.data,
    #         serializer.data
    #     )

    def test_filter_movie_sessions(self):
    #     # response = self.client.get(MOVIE_SESSION_URL, {"movie": 1})
    #     self.sample_movie_session__()
    #     response = self.client.get(MOVIE_SESSION_URL)
    #
    #     serializer1 = MovieSessionListSerializer(
    #         self.sample_movie_session__(), many=False
    #     )
    #
    #     self.assertIn(serializer1.data, response.data)

    # def test_filter_movie_sessions_by_movie_id(self):
    #     # Create movies and sessions
    #     movie1 = Movie.objects.create(title="Movie 1", description="Description 1", duration=120)
    #     movie2 = Movie.objects.create(title="Movie 2", description="Description 2", duration=90)
    #     cinema_hall = CinemaHall.objects.create(name="Cinema Hall 1", rows=10, seats_in_row=10)
    #
    #     session1 = MovieSession.objects.create(show_time="2023-06-30T15:30:00Z", movie=movie1, cinema_hall=cinema_hall)
    #     session2 = MovieSession.objects.create(show_time="2023-06-30T18:30:00Z", movie=movie1, cinema_hall=cinema_hall)
    #     session3 = MovieSession.objects.create(show_time="2023-06-30T20:00:00Z", movie=movie2, cinema_hall=cinema_hall)
    #
    #
    #     movies = Movie.objects.all()
    #     sessions = MovieSession.objects.all()
    #     cinema_hall = CinemaHall.objects.all()
    #
        # Filter sessions by movie_id=1
        response = self.client.get(MOVIE_SESSION_URL, {"movie": "1"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    #
    #     # serializer = MovieSessionListSerializer([session1, session2], many=True)
    #     # self.assertEqual(response.data, serializer.data)
    #
    #     # # Filter sessions by movie_id=2
    #     # response = self.client.get(MOVIE_SESSION_URL, {"?movie": "2"})
    #     # self.assertEqual(response.status_code, status.HTTP_200_OK)
    #     #
    #     # serializer = MovieSessionListSerializer([session3], many=True)
    #     # self.assertEqual(response.data, serializer.data)