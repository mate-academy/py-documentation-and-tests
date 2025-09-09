from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from cinema.models import Movie, CinemaHall, MovieSession, Order, Ticket
from django.contrib.auth import get_user_model
from datetime import datetime

User = get_user_model()

class OrderViewSetTestCase(TestCase):
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

    def test_list_orders_empty(self):
        url = reverse("cinema:order-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 0)

    def test_create_order(self):
        url = reverse("cinema:order-list")
        data = {
            "tickets": [
                {"row": 1, "seat": 1, "movie_session": self.session.id},
                {"row": 1, "seat": 2, "movie_session": self.session.id},
            ]
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(Order.objects.first().tickets.count(), 2)
