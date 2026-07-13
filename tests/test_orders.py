from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from cinema.models import Movie, CinemaHall, MovieSession, Order, Ticket
from user.models import User
from datetime import datetime


class OrderViewSetTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@test.com", password="pass1234"
        )
        refresh = RefreshToken.for_user(self.user)
        self.token = str(refresh.access_token)

        self.movie = Movie.objects.create(
            title="Order Movie", description="Desc", duration=90
        )
        self.hall = CinemaHall.objects.create(
            name="Hall 2", rows=5, seats_in_row=5
        )
        self.session = MovieSession.objects.create(
            show_time=datetime(2026, 7, 12, 20, 0),
            movie=self.movie,
            cinema_hall=self.hall,
        )

        self.url = reverse("cinema:order-list")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

    def test_list_orders_authorized(self):
        order = Order.objects.create(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.data["count"], 1)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], order.id)

    def test_create_order_with_ticket(self):
        payload = {
            "tickets": [
                {"row": 1, "seat": 1, "movie_session": self.session.id}
            ]
        }
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(Ticket.objects.count(), 1)

        order = Order.objects.first()
        ticket = Ticket.objects.first()
        self.assertEqual(order.user, self.user)
        self.assertEqual(ticket.movie_session, self.session)
        self.assertEqual(ticket.row, 1)
        self.assertEqual(ticket.seat, 1)

