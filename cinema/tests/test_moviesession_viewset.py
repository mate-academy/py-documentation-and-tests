from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from cinema.models import MovieSession, Movie, CinemaHall
from django.contrib.auth import get_user_model
from datetime import datetime

User = get_user_model()

class MovieSessionViewSetTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="admin.user@cinema.com", password="1qazcde3"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.movie = Movie.objects.create(title="Test Movie", description="Desc", duration=120)
        self.cinema_hall = CinemaHall.objects.create(name="Hall 1", rows=5, seats_in_row=10)
        self.session = MovieSession.objects.create(
            movie=self.movie,
            cinema_hall=self.cinema_hall,
            show_time=datetime(2025, 9, 9, 18, 0)
        )

    def test_list_sessions(self):
        url = reverse("cinema:moviesession-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_filter_sessions_by_date(self):
        url = reverse("cinema:moviesession-list") + "?date=2025-09-09"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_filter_sessions_by_movie(self):
        url = reverse("cinema:moviesession-list") + f"?movie={self.movie.id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
