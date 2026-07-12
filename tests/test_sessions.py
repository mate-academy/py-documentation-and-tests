from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from datetime import datetime

from cinema.models import Movie, CinemaHall, MovieSession
from user.models import User


class MovieSessionViewSetTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@test.com", password="pass1234"
        )
        refresh = RefreshToken.for_user(self.user)
        self.token = str(refresh.access_token)

        self.movie = Movie.objects.create(
            title="Session Movie", description="Desc", duration=100
        )
        self.hall = CinemaHall.objects.create(
            name="Hall 1", rows=10, seats_in_row=10
        )
        self.session = MovieSession.objects.create(
            show_time=datetime(2026, 7, 12, 18, 0),
            movie=self.movie,
            cinema_hall=self.hall,
        )

        self.url = reverse("cinema:moviesession-list")

    def test_list_sessions_authorized(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_filter_sessions_by_date(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")
        response = self.client.get(self.url, {"date": "2026-07-12"})
        self.assertEqual(len(response.data), 1)

    def test_filter_sessions_by_movie(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")
        response = self.client.get(self.url, {"movie": str(self.movie.id)})
        self.assertEqual(len(response.data), 1)
