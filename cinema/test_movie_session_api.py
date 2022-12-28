from django.contrib.auth import get_user_model
from django.db.models import F, Count
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor
from cinema.serializers import (
    MovieSessionListSerializer,
    MovieSessionDetailSerializer
)

MOVIE_URL = reverse("cinema:movie-list")
MOVIE_SESSION_URL = reverse("cinema:moviesession-list")


def sample_movie(**params):
    defaults = {
        "title": "Sample movie",
        "description": "Sample description",
        "duration": 193,
    }
    defaults.update(params)

    return Movie.objects.create(**defaults)


def sample_genre(**params):
    defaults = {
        "name": "Comedy",
    }
    defaults.update(params)

    return Genre.objects.create(**defaults)


def sample_actor(**params):
    defaults = {"first_name": "Elon", "last_name": "Mask"}
    defaults.update(params)

    return Actor.objects.create(**defaults)


def sample_movie_session(**params):
    cinema_hall = CinemaHall.objects.create(
        name="Agate", rows=35, seats_in_row=30
    )

    defaults = {
        "show_time": "2022-12-28 13:00:00",
        "movie": None,
        "cinema_hall": cinema_hall,
    }
    defaults.update(params)

    return MovieSession.objects.create(**defaults)


def detail_url(movie_id):
    return reverse("cinema:moviesession-detail", args=[movie_id])


class UnauthenticatedMovieSessionTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_SESSION_URL)
        detail_res = self.client.get(detail_url(1))

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(detail_res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieSessionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "user@myproject.com", "password1234"
        )
        self.client.force_authenticate(self.user)
        self.comedy_genre = sample_genre()
        self.horror_genre = sample_genre(name="Horror")
        self.actor = sample_actor()
        self.horror_movie = sample_movie()
        self.horror_movie.genres.set([self.horror_genre])
        self.comedy_movie = sample_movie()
        self.comedy_movie.genres.set([self.comedy_genre])
        self.horror_movie_session = sample_movie_session(
            movie=self.horror_movie,
        )
        self.comedy_movie_session = sample_movie_session(
            movie=self.comedy_movie,
            show_time="2022-10-01 13:00:00"
        )
        self.movie_session = (
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
        self.serializer = MovieSessionListSerializer(
            self.movie_session,
            many=True
        )

    def test_list_movie_sessions(self):
        res = self.client.get(MOVIE_SESSION_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, self.serializer.data)

    def test_filter_movie_session_by_date(self):
        res = self.client.get(MOVIE_SESSION_URL, {"date": "2022-12-28"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertIn(res.data[0], self.serializer.data)

    def test_filter_movie_session_by_movie_id(self):
        res = self.client.get(MOVIE_SESSION_URL, {"movie": "1"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertIn(res.data[0], self.serializer.data)

    def test_retrieve_movie_session_detail(self):
        res = self.client.get(detail_url(self.horror_movie_session.id))
        serializer = MovieSessionDetailSerializer(self.horror_movie_session)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], serializer.data["id"])

    def test_create_movie_session_forbidden(self):
        payload = {
            "show_time": "2022-12-28 13:00:00",
            "movie": 1,
            "cinema_hall": 1,
        }
        res = self.client.post(MOVIE_SESSION_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieSessionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@myproject.com",
            "password",
            is_staff=True
        )
        self.client.force_authenticate(self.user)
        self.movie = sample_movie()
        self.genre = sample_genre()
        self.actor = sample_actor()
        self.movie_session = sample_movie_session(movie=self.movie)

    def test_create_movie_session_forbidden(self):
        payload = {
            "show_time": "2022-12-28 13:00:00",
            "movie": self.movie.id,
            "cinema_hall": 1,
        }
        res = self.client.post(MOVIE_SESSION_URL, payload)
        movie_session = MovieSession.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["movie"], movie_session.movie.id)
        self.assertEqual(res.data["cinema_hall"], movie_session.cinema_hall.id)
