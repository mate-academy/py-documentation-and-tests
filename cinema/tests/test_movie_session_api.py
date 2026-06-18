from django.contrib.auth import get_user_model
from django.db.models import Count, F
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from cinema.models import Movie, MovieSession, CinemaHall
from cinema.serializers import MovieSessionListSerializer, MovieSessionDetailSerializer

MOVIE_SESSION_URL = reverse("cinema:moviesession-list")


def detail_url(session_id):
    return reverse("cinema:moviesession-detail", args=[session_id])


def sample_movie(**params):
    defaults = {
        "title": "Sample movie",
        "description": "Sample description",
        "duration": 90,
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)


def sample_cinema_hall(**params):
    defaults = {
        "name": "Main Hall",
        "rows": 10,
        "seats_in_row": 10,
    }
    defaults.update(params)
    return CinemaHall.objects.create(**defaults)


def sample_movie_session(**params):
    movie = sample_movie()
    cinema_hall = sample_cinema_hall()
    defaults = {
        "show_time": "2026-06-19 20:00:00",
        "movie": movie,
        "cinema_hall": cinema_hall,
    }
    defaults.update(params)
    return MovieSession.objects.create(**defaults)


class UnauthenticatedMovieSessionApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_SESSION_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieSessionApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@user.com",
            password="password123"
        )
        self.client.force_authenticate(self.user)

    def test_list_movie_sessions(self):
        session = sample_movie_session()
        res = self.client.get(MOVIE_SESSION_URL)

        sessions = MovieSession.objects.annotate(
            tickets_available=F("cinema_hall__rows") * F("cinema_hall__seats_in_row") - Count("tickets")
        )
        serializer = MovieSessionListSerializer(sessions.get(id=session.id))

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer.data, res.data)

    def test_filter_sessions_by_date(self):
        session1 = sample_movie_session(show_time="2026-06-19 20:00:00")
        session2 = sample_movie_session(show_time="2026-06-20 20:00:00")

        res = self.client.get(MOVIE_SESSION_URL, {"date": "2026-06-19"})

        sessions = MovieSession.objects.annotate(
            tickets_available=F("cinema_hall__rows") * F("cinema_hall__seats_in_row") - Count("tickets")
        )

        session1_data = MovieSessionListSerializer(sessions.get(id=session1.id)).data
        session2_data = MovieSessionListSerializer(sessions.get(id=session2.id)).data

        self.assertIn(session1_data, res.data)
        self.assertNotIn(session2_data, res.data)

    def test_filter_sessions_by_movie_id(self):
        movie1 = sample_movie(title="Movie 1")
        movie2 = sample_movie(title="Movie 2")
        session1 = sample_movie_session(movie=movie1)
        session2 = sample_movie_session(movie=movie2)

        res = self.client.get(MOVIE_SESSION_URL, {"movie": movie1.id})

        sessions = MovieSession.objects.annotate(
            tickets_available=F("cinema_hall__rows") * F("cinema_hall__seats_in_row") - Count("tickets")
        )

        session1_data = MovieSessionListSerializer(sessions.get(id=session1.id)).data
        session2_data = MovieSessionListSerializer(sessions.get(id=session2.id)).data

        self.assertIn(session1_data, res.data)
        self.assertNotIn(session2_data, res.data)

    def test_retrieve_movie_session_detail(self):
        session = sample_movie_session()
        url = detail_url(session.id)
        res = self.client.get(url)

        session.refresh_from_db()
        serializer = MovieSessionDetailSerializer(session)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_session_forbidden(self):
        movie = sample_movie()
        cinema_hall = sample_cinema_hall()
        payload = {
            "show_time": "2026-06-19 20:00:00",
            "movie": movie.id,
            "cinema_hall": cinema_hall.id,
        }
        res = self.client.post(MOVIE_SESSION_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieSessionApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@user.com",
            password="password123",
            is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_movie_session(self):
        movie = sample_movie()
        cinema_hall = sample_cinema_hall()
        payload = {
            "show_time": "2026-06-19T20:00:00Z",
            "movie": movie.id,
            "cinema_hall": cinema_hall.id,
        }

        res = self.client.post(MOVIE_SESSION_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
