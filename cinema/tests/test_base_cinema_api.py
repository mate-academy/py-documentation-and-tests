from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from cinema.models import Genre, Actor, CinemaHall
from cinema.serializers import GenreSerializer, ActorSerializer, CinemaHallSerializer

GENRE_URL = reverse("cinema:genre-list")
ACTOR_URL = reverse("cinema:actor-list")
CINEMA_HALL_URL = reverse("cinema:cinemahall-list")


class AuthenticatedBaseCinemaApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@user.com",
            password="password123"
        )
        self.client.force_authenticate(self.user)

    def test_list_genres(self):
        Genre.objects.create(name="Action")
        Genre.objects.create(name="Comedy")

        res = self.client.get(GENRE_URL)

        genres = Genre.objects.all()
        serializer = GenreSerializer(genres, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_genre_forbidden(self):
        payload = {"name": "Thriller"}
        res = self.client.post(GENRE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_actors(self):
        Actor.objects.create(first_name="John", last_name="Doe")
        res = self.client.get(ACTOR_URL)

        actors = Actor.objects.all()
        serializer = ActorSerializer(actors, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_actor_forbidden(self):
        payload = {"first_name": "Marc", "last_name": "Smith"}
        res = self.client.post(ACTOR_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_cinema_halls(self):
        CinemaHall.objects.create(name="Blue", rows=5, seats_in_row=5)
        res = self.client.get(CINEMA_HALL_URL)

        halls = CinemaHall.objects.all()
        serializer = CinemaHallSerializer(halls, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_cinema_hall_forbidden(self):
        payload = {"name": "Red", "rows": 10, "seats_in_row": 10}
        res = self.client.post(CINEMA_HALL_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminBaseCinemaApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@user.com",
            password="password123",
            is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_genre(self):
        payload = {"name": "Sci-Fi"}
        res = self.client.post(GENRE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Genre.objects.filter(name="Sci-Fi").exists())

    def test_create_actor(self):
        payload = {"first_name": "Brad", "last_name": "Pitt"}
        res = self.client.post(ACTOR_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Actor.objects.filter(first_name="Brad", last_name="Pitt").exists())

    def test_create_cinema_hall(self):
        payload = {"name": "IMAX", "rows": 15, "seats_in_row": 20}
        res = self.client.post(CINEMA_HALL_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(CinemaHall.objects.filter(name="IMAX").exists())
