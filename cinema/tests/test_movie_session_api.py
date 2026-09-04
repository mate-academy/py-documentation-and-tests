from django.contrib.auth import get_user_model
from django.db.models import Model, F, Count
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall, Ticket, Order
from cinema.serializers import (
    MovieSessionListSerializer,
    MovieSessionDetailSerializer,
)


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
    defaults = {"name": "Test Hall", "rows": 10, "seats_in_row": 5}

    defaults.update(params)
    return CinemaHall.objects.create(**defaults)


def sample_movie_session(**params):
    cinema_hall = CinemaHall.objects.create(
        name="Blue", rows=20, seats_in_row=20
    )

    movie = Movie.objects.create(
        title="Sample movie",
        description="Sample description",
        duration=90,
    )

    defaults = {
        "show_time": "2022-06-02 14:00:00",
        "movie": movie,
        "cinema_hall": cinema_hall,
    }
    defaults.update(params)

    return MovieSession.objects.create(**defaults)


def get_movie_session_queryset():
    return MovieSession.objects.all().annotate(
        tickets_available=(
            F("cinema_hall__rows") * F("cinema_hall__seats_in_row")
            - Count("tickets")
        )
    )


def detail_url(movie_session_id):
    return reverse("cinema:moviesession-detail", args=[movie_session_id])


class UnauthenticatedCinemaAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_SESSION_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedCinemaAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.test", password="testpassword"
        )
        self.client.force_authenticate(self.user)

    def test_authenticated_can_not_update(self):
        movie_session = sample_movie_session()

        payload = {
            "show_time": "2022-06-02 14:00:00",
        }

        result = self.client.put(detail_url(movie_session.id), payload)

        self.assertEqual(result.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_can_not_partial_update(self):
        movie_session = sample_movie_session()

        payload = {"show_time": "2022-06-02 14:00:00"}

        result = self.client.patch(detail_url(movie_session.id), payload)
        self.assertEqual(result.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_can_not_delete(self):
        movie_session = sample_movie_session()

        result = self.client.delete(detail_url(movie_session.id))
        self.assertEqual(result.status_code, status.HTTP_403_FORBIDDEN)

    def test_tickets_available(self):
        session = sample_movie_session()
        order = Order.objects.create(user=self.user)
        num_tickets = 3

        for i in range(num_tickets):
            Ticket.objects.create(
                movie_session=session, row=1, order=order, seat=i + 1
            )

        result = self.client.get(MOVIE_SESSION_URL)
        self.assertEqual(
            result.data[0]["tickets_available"],
            session.cinema_hall.capacity - num_tickets,
        )

    def test_cinema_list(self):
        movie_1 = sample_movie(title="Movie1")
        movie_2 = sample_movie(title="Movie2")
        movie_session_1 = sample_movie_session(movie=movie_1)
        movie_session_2 = sample_movie_session(movie=movie_2)

        result = self.client.get(MOVIE_SESSION_URL)
        movie_sessions = get_movie_session_queryset()
        serializer = MovieSessionListSerializer(movie_sessions, many=True)

        self.assertEqual(result.data, serializer.data)
        self.assertEqual(result.status_code, status.HTTP_200_OK)

    def test_cinema_retrieve(self):
        movie = sample_movie(title="Movie")
        movie_session = sample_movie_session(movie=movie)

        result = self.client.get(detail_url(movie_session.id))
        movie_session = get_movie_session_queryset().get(id=movie_session.id)
        serializer = MovieSessionDetailSerializer(movie_session)

        self.assertEqual(result.data, serializer.data)
        self.assertEqual(result.status_code, status.HTTP_200_OK)


class AdminCinemaTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@admin.test", password="adminpassword", is_staff=True
        )
        self.client.force_authenticate(self.user)
