from django.core.cache import cache
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from cinema.models import Order, Ticket
from cinema.serializers import OrderListSerializer
from cinema.tests.test_base import sample_user, sample_movie_session

ORDER_URL = reverse("cinema:order-list")


class UnauthenticatedOrderTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(ORDER_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedOrderTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.user = sample_user()
        self.client.force_authenticate(user=self.user)
        self.movie_session = sample_movie_session()

    def test_order_list(self):
        order = Order.objects.create(user=self.user)
        Ticket.objects.create(
            order=order, movie_session=self.movie_session, row=1, seat=1
        )

        res = self.client.get(ORDER_URL)

        serializer = OrderListSerializer(
            Order.objects.filter(user=self.user), many=True
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"], serializer.data)

    def test_order_list_only_own_orders(self):
        other_user = sample_user(email="other@test.com")
        own_order = Order.objects.create(user=self.user)
        Order.objects.create(user=other_user)

        res = self.client.get(ORDER_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 1)
        self.assertEqual(res.data["results"][0]["id"], own_order.id)

    def test_order_list_is_paginated(self):
        for _ in range(11):
            Order.objects.create(user=self.user)

        res = self.client.get(ORDER_URL)

        self.assertEqual(res.data["count"], 11)
        self.assertEqual(len(res.data["results"]), 10)  # page_size
        self.assertIsNotNone(res.data["next"])

    def test_create_order(self):
        payload = {
            "tickets": [
                {"row": 1, "seat": 1, "movie_session": self.movie_session.pk},
                {"row": 1, "seat": 2, "movie_session": self.movie_session.pk},
            ]
        }
        res = self.client.post(ORDER_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        order = Order.objects.get(pk=res.data["id"])
        self.assertEqual(order.user, self.user)
        self.assertEqual(order.tickets.count(), 2)

    def test_create_order_without_tickets(self):
        res = self.client.post(ORDER_URL, {"tickets": []}, format="json")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Order.objects.exists())

    def test_create_order_with_invalid_seat(self):
        payload = {
            "tickets": [
                {
                    "row": 9999,
                    "seat": 1,
                    "movie_session": self.movie_session.pk,
                },
            ]
        }
        res = self.client.post(ORDER_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Order.objects.exists())

    def test_create_order_is_atomic(self):
        payload = {
            "tickets": [
                {"row": 1, "seat": 1, "movie_session": self.movie_session.pk},
                {
                    "row": 9999,
                    "seat": 1,
                    "movie_session": self.movie_session.pk,
                },
            ]
        }
        res = self.client.post(ORDER_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Order.objects.exists())
        self.assertFalse(Ticket.objects.exists())
