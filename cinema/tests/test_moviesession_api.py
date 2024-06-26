from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils.timezone import now
from rest_framework.test import APIClient

from cinema.models import MovieSession, Movie, CinemaHall
from cinema.serializers import (
    MovieSessionListSerializer,
    MovieSessionDetailSerializer,
)
from cinema.views import MovieSessionViewSet


class MovieSessionTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.user = get_user_model().objects.create_user(
            "user@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)

        self.movie = Movie.objects.create(title="Sample Movie", duration=120)
        self.cinema_hall = CinemaHall.objects.create(
            name="Sample Cinema Hall", rows=5, seats_in_row=10
        )
        self.session1 = MovieSession.objects.create(
            show_time=now() + timedelta(days=1),
            movie=self.movie,
            cinema_hall=self.cinema_hall,
        )
        self.session2 = MovieSession.objects.create(
            show_time=now() + timedelta(days=2),
            movie=self.movie,
            cinema_hall=self.cinema_hall,
        )

    def test_list_movie_sessions(self):
        response = self.client.get("/api/cinema/movie_sessions/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    def test_retrieve_movie_session(self):
        response = self.client.get(f"/api/cinema/movie_sessions/{self.session1.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], self.session1.id)

    def test_filter_by_date(self):
        date = (now() + timedelta(days=1)).date()
        response = self.client.get(f"/api/cinema/movie_sessions/?date={date}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.session1.id)

    def test_filter_by_movie(self):
        response = self.client.get(f"/api/cinema/movie_sessions/?movie={self.movie.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    def test_serializer_class_list_action(self):
        view = MovieSessionViewSet()
        view.action = "list"
        serializer_class = view.get_serializer_class()
        self.assertEqual(serializer_class, MovieSessionListSerializer)

    def test_serializer_class_retrieve_action(self):
        view = MovieSessionViewSet()
        view.action = "retrieve"
        serializer_class = view.get_serializer_class()
        self.assertEqual(serializer_class, MovieSessionDetailSerializer)

    def test_permission_class(self):
        response = self.client.post(
            "/api/cinema/movie_sessions/",
            data={
                "show_time": now() + timedelta(days=1),
                "movie": self.movie.id,
                "cinema_hall": self.cinema_hall.id,
            },
        )
        self.assertEqual(response.status_code, 403)

        response = self.client.put(
            "/api/cinema/movie_sessions/",
            data={
                "show_time": now() + timedelta(days=1),
                "movie": self.movie.id,
                "cinema_hall": self.cinema_hall.id,
            },
        )
        self.assertEqual(response.status_code, 403)

        response = self.client.delete(
            f"/api/cinema/movie_sessions/{self.session1.id}/",
        )
        self.assertEqual(response.status_code, 403)

        self.user.is_staff = True
        self.user.save()

        response = self.client.post(
            "/api/cinema/movie_sessions/",
            data={
                "show_time": now() + timedelta(days=1),
                "movie": self.movie.id,
                "cinema_hall": self.cinema_hall.id,
            },
        )
        self.assertEqual(response.status_code, 201)

        response = self.client.put(
            "/api/cinema/movie_sessions/",
            data={
                "show_time": now() + timedelta(days=1),
                "movie": self.movie.id,
                "cinema_hall": self.cinema_hall.id,
            },
        )
        self.assertEqual(response.status_code, 405)

        response = self.client.delete(
            f"/api/cinema/movie_sessions/{self.session1.id}/",
        )
        self.assertEqual(response.status_code, 204)
