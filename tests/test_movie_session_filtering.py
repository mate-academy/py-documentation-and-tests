from datetime import datetime, date
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor


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
        "name": "Blue",
        "rows": 20,
        "seats_in_row": 20,
    }
    defaults.update(params)
    return CinemaHall.objects.create(**defaults)


def sample_movie_session(**params):
    defaults = {
        "show_time": "2022-06-02 14:00:00",
    }
    defaults.update(params)
    return MovieSession.objects.create(**defaults)


class MovieSessionFilteringTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@example.com", password="testpass123"
        )

        self.movie1 = sample_movie(title="Movie 1")
        self.movie2 = sample_movie(title="Movie 2")

        self.cinema_hall1 = sample_cinema_hall(name="Hall 1")
        self.cinema_hall2 = sample_cinema_hall(name="Hall 2")

        self.session1 = MovieSession.objects.create(
            show_time=datetime(2022, 6, 1, 14, 0, 0),
            movie=self.movie1,
            cinema_hall=self.cinema_hall1,
        )

        self.session2 = MovieSession.objects.create(
            show_time=datetime(2022, 6, 2, 16, 0, 0),
            movie=self.movie1,
            cinema_hall=self.cinema_hall2,
        )

        self.session3 = MovieSession.objects.create(
            show_time=datetime(2022, 6, 2, 18, 0, 0),
            movie=self.movie2,
            cinema_hall=self.cinema_hall1,
        )

        self.session4 = MovieSession.objects.create(
            show_time=datetime(2022, 6, 3, 20, 0, 0),
            movie=self.movie2,
            cinema_hall=self.cinema_hall2,
        )

    def tearDown(self):

        MovieSession.objects.all().delete()
        Movie.objects.all().delete()
        CinemaHall.objects.all().delete()

    def test_list_movie_sessions_without_filters(self):

        url = reverse("cinema:moviesession-list")
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIsInstance(res.data, list)

    def test_filter_movie_sessions_by_date(self):
        url = reverse("cinema:moviesession-list")
        res = self.client.get(url, {"date": "2022-06-02"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)

        for session_data in res.data:
            session_date = datetime.fromisoformat(
                session_data["show_time"].replace("Z", "+00:00")
            ).date()
            self.assertEqual(session_date, date(2022, 6, 2))

    def test_filter_movie_sessions_by_movie(self):
        url = reverse("cinema:moviesession-list")
        res = self.client.get(url, {"movie": self.movie1.id})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)

        for session_data in res.data:
            self.assertEqual(session_data["movie_title"], "Movie 1")

    def test_filter_movie_sessions_by_date_and_movie(self):
        url = reverse("cinema:moviesession-list")
        res = self.client.get(url, {"date": "2022-06-02", "movie": self.movie1.id})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["movie_title"], "Movie 1")

        session_date = datetime.fromisoformat(
            res.data[0]["show_time"].replace("Z", "+00:00")
        ).date()
        self.assertEqual(session_date, date(2022, 6, 2))

    def test_filter_movie_sessions_invalid_date_format(self):
        url = reverse("cinema:moviesession-list")
        res = self.client.get(url, {"date": "invalid-date"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 0)

    def test_filter_movie_sessions_nonexistent_movie(self):
        url = reverse("cinema:moviesession-list")
        res = self.client.get(url, {"movie": 99999})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 0)

    def test_movie_session_serializer_classes(self):
        url = reverse("cinema:moviesession-list")
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        session_data = res.data[0]
        self.assertIn("movie_title", session_data)
        self.assertIn("movie_image", session_data)
        self.assertIn("cinema_hall_name", session_data)
        self.assertIn("cinema_hall_capacity", session_data)
        self.assertIn("tickets_available", session_data)

        detail_url = reverse("cinema:moviesession-detail", args=[self.session1.id])
        res = self.client.get(detail_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        session_data = res.data
        self.assertIn("movie", session_data)
        self.assertIn("cinema_hall", session_data)
        self.assertIn("taken_places", session_data)

    def test_movie_session_ordering(self):
        url = reverse("cinema:moviesession-list")
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIsInstance(res.data, list)
