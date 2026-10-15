from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from cinema.models import CinemaHall
from cinema.serializers import CinemaHallSerializer
from cinema.tests.test_base import (
    sample_user,
    sample_cinema_hall,
    sample_admin_user,
)

CINEMA_HALL_URL = reverse("cinema:cinema_hall-list")


class UnauthenticatedCinemaHallTests(TestCase):
    def test_auth_required(self):
        res = self.client.get(CINEMA_HALL_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedCinemaHallTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = sample_user()
        self.client.force_authenticate(user=self.user)

    def test_cinema_hall_list(self):
        sample_cinema_hall()
        res = self.client.get(CINEMA_HALL_URL)

        cinema_halls = CinemaHall.objects.all()
        serializer = CinemaHallSerializer(cinema_halls, many=True)

        self.assertEqual(res.data, serializer.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_create_cinema_hall_forbidden(self):
        payload = {"name": "Hall", "rows": 12, "seats_in_row": 22}
        res = self.client.post(CINEMA_HALL_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminCinemaHallTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = sample_admin_user()
        self.client.force_authenticate(user=self.user)

    def test_create_cinema_hall(self):
        payload = {"name": "Hall", "rows": 12, "seats_in_row": 22}

        res = self.client.post(CINEMA_HALL_URL, payload)
        cinema_hall = CinemaHall.objects.get(id=res.data["id"])
        serializer = CinemaHallSerializer(cinema_hall)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data, serializer.data)
