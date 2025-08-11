from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import Genre, Actor, CinemaHall
from cinema.serializers import (
    ActorSerializer,
    GenreSerializer,
    CinemaHallSerializer,
)


class UnauthenticatedActorApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(reverse("cinema:actor-list"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedActorApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user@test.com",
            password="testPass1"
        )
        self.client.force_authenticate(user=self.user)

    def test_actor_list(self):
        response = self.client.get(reverse("cinema:actor-list"))
        actors = Actor.objects.all()
        serializer = ActorSerializer(actors, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_admin_rights_required(self):
        data = {
            "first_name": "John",
            "last_name": "Doe"
        }
        response = self.client.post(reverse("cinema:actor-list"), data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminActorApiTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            email="admin@admin.com",
            password="adminPass1"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

    def test_actor_create(self):
        data = {
            "first_name": "Actor",
            "last_name": "Test"
        }
        response = self.client.post(
            reverse("cinema:actor-list"),
            data
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        actor = Actor.objects.get(id=response.data["id"])
        self.assertEqual(actor.first_name, data["first_name"])
        self.assertEqual(actor.last_name, data["last_name"])


class UnauthenticatedGenreApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(reverse("cinema:genre-list"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedGenreApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user@test.com",
            password="userPass1"
        )
        self.client.force_authenticate(user=self.user)

    def test_genre_list(self):
        response = self.client.get(reverse("cinema:genre-list"))
        genres = Genre.objects.all()
        serializer = GenreSerializer(genres, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_admin_rights_required(self):
        data = {
            "first_name": "John",
            "last_name": "Doe"
        }
        response = self.client.post(reverse("cinema:genre-list"), data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminGenreApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            email="user@test.com",
            password="userPass1"
        )
        self.client.force_authenticate(user=self.user)

    def test_genre_create(self):
        data = {
            "name": "Test Genre"
        }
        response = self.client.post(
            reverse("cinema:genre-list"),
            data
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        genre = Genre.objects.get(id=response.data["id"])
        self.assertEqual(genre.name, data["name"])


class UnauthenticatedCinemaHallApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(reverse("cinema:cinemahall-list"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedCinemaHallApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user@test.com",
            password="testPass1"
        )
        self.client.force_authenticate(user=self.user)

    def test_cinema_hall_list(self):
        response = self.client.get(reverse("cinema:cinemahall-list"))
        cinema_halls = CinemaHall.objects.all()
        serializer = CinemaHallSerializer(cinema_halls, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_admin_rights_required(self):
        data = {
            "first_name": "John",
            "last_name": "Doe"
        }
        response = self.client.post(reverse("cinema:genre-list"), data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminCinemaHallApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            email="admin@admin.com",
            password="adminPass1"
        )
        self.client.force_authenticate(user=self.user)

    def test_create_cinema_hall(self):
        data = {
            "name": "testHall",
            "rows": 4,
            "seats_in_row": 10
        }
        response = self.client.post(
            reverse("cinema:cinemahall-list"),
            data
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        cinema_hall = CinemaHall.objects.get(id=response.data["id"])
        self.assertEqual(response.data["name"], cinema_hall.name)

    def test_create_cinema_hall_with_invalid_data(self):
        data = {
            "name": "testHall",
            "rows": "invalid data",
            "seats_in_row": "10"
        }
        response = self.client.post(
            reverse("cinema:cinemahall-list"),
            data
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
