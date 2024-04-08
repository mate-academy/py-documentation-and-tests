from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Order


class UnauthenticatedOrderApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(reverse("cinema:order-list"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedOrderApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user@test.com",
            password="testPass1"
        )
        self.client.force_authenticate(user=self.user)
        self.movie = Movie.objects.create(
            title="testMovie",
            description="test Description",
            duration=80
        )
        self.genre = Genre.objects.create(
            name="testGenre"
        )
        self.order = Order.objects.create(
            user=self.user
        )

    def test_order_list(self):
        response = self.client.get(reverse("cinema:order-list"))
        orders = Order.objects.filter(user=self.user)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), orders.count())
