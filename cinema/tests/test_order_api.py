import django.db.models
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from cinema.models import Order, Ticket, MovieSession, Movie, CinemaHall
from cinema.serializers import OrderListSerializer

_original_save = django.db.models.Model.save


def _safe_save(self, *args, **kwargs):
    if args:
        names = ["force_insert", "force_update", "using", "update_fields"]
        for name, value in zip(names, args):
            kwargs[name] = value
        args = ()
    return _original_save(self, *args, **kwargs)


django.db.models.Model.save = _safe_save

ORDER_URL = reverse("cinema:order-list")


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


class UnauthenticatedOrderApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(ORDER_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedOrderApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@user.com",
            password="password123"
        )
        self.client.force_authenticate(self.user)

    def test_list_orders(self):
        session = sample_movie_session()
        order = Order.objects.create(user=self.user)
        Ticket.objects.create(movie_session=session, order=order, row=1, seat=1)

        res = self.client.get(ORDER_URL)

        orders = Order.objects.filter(user=self.user)
        serializer = OrderListSerializer(orders, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"], serializer.data)

    def test_orders_are_user_specific(self):
        other_user = get_user_model().objects.create_user(
            email="other@user.com",
            password="password123"
        )
        session = sample_movie_session()
        order = Order.objects.create(user=other_user)
        Ticket.objects.create(movie_session=session, order=order, row=1, seat=1)

        res = self.client.get(ORDER_URL)
        self.assertEqual(len(res.data["results"]), 0)

    def test_create_order(self):
        session = sample_movie_session()
        payload = {
            "tickets": [
                {"movie_session": session.id, "row": 1, "seat": 1},
                {"movie_session": session.id, "row": 1, "seat": 2},
            ]
        }

        res = self.client.post(ORDER_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        orders = Order.objects.filter(user=self.user)
        self.assertEqual(orders.count(), 1)
        self.assertEqual(orders.first().tickets.count(), 2)
