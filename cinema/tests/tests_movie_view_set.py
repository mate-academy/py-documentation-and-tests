from cinema.serializers import MovieSessionSerializer
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.db.models import F, Count

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor
from cinema.serializers import (
    MovieSessionListSerializer,
    MovieSessionSerializer,
    MovieSessionDetailSerializer,
)


MOVIE_SESSION_LIST_URL = reverse("cinema:moviesession-list")


def sample_movie_sessions(**params):
    SCIFI = Genre.objects.create(name="Sci-Fi")
    HORROR = Genre.objects.create(name="Horror")
    ACTION = Genre.objects.create(name="Action")
    COMEDY = Genre.objects.create(name="Comedy")

    ARNY = Actor.objects.create(first_name="Arnold", last_name="Schwarzenegger")
    LINDA = Actor.objects.create(first_name="Linda", last_name="Hamilton")
    ALAN = Actor.objects.create(first_name="Alan", last_name="Tudyk")

    MOVIE_1 = Movie.objects.create(
        title="Terminator",
        description="Robots, bang-bang",
        duration=100,
    )
    MOVIE_1.actors.add(ARNY, LINDA)
    MOVIE_1.genres.add(SCIFI, ACTION)

    MOVIE_2 = Movie.objects.create(
        title="Resident Alien",
        description="Shoes, chavk-chavk",
        duration=10,
    )
    MOVIE_2.actors.add(LINDA, ALAN)
    MOVIE_2.genres.add(SCIFI, COMEDY)

    RED = CinemaHall.objects.create(name="Red", rows=10, seats_in_row=10)
    BLUE = CinemaHall.objects.create(name="Blue", rows=12, seats_in_row=12)

    MovieSession.objects.create(
        show_time="2024-10-08 13:00:00", movie=MOVIE_1, cinema_hall=RED
    )
    MovieSession.objects.create(
        show_time="2024-10-09 13:00:00", movie=MOVIE_2, cinema_hall=BLUE
    )


class UnauthenticatedUserTest(TestCase):
    def setup(self):
        self.client = APIClient()
        sample_movie_sessions()

    def test_auth_required(self):
        response = self.client.get(MOVIE_SESSION_LIST_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        response = self.client.get(MOVIE_SESSION_LIST_URL + "1/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        response = self.client.delete(MOVIE_SESSION_LIST_URL + "1/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        payload = {
            "show_time": "2024-10-12T13:00:00Z",
            "movie": 2,
            "cinema_hall": 2,
        }
        response = self.client.post(MOVIE_SESSION_LIST_URL, data=payload)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        response = self.client.put((MOVIE_SESSION_LIST_URL + "1/"), data=payload)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        payload = {
            "movie": 2,
        }
        response = self.client.put((MOVIE_SESSION_LIST_URL + "1/"), data=payload)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedUserTest(TestCase):
    def setUp(self):
        sample_movie_sessions()
        self.user = get_user_model().objects.create_user(
            email="test@test.test",
            password="<PASSWORD>",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.movie_sessions_list = MovieSession.objects.all().annotate(
            tickets_available=(
                F("cinema_hall__rows") * F("cinema_hall__seats_in_row")
                - Count("tickets")
            )
        )

    def test_movie_sessions_list(self):
        movie_sessions = self.movie_sessions_list
        serializer = MovieSessionListSerializer(movie_sessions, many=True)
        response = self.client.get(MOVIE_SESSION_LIST_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_movie_sessions_list_with_filter_by_date(self):
        response = self.client.get(MOVIE_SESSION_LIST_URL, {"date": "2024-10-09"})
        movie_sessions = self.movie_sessions_list.filter(show_time__date="2024-10-09")
        serializer = MovieSessionListSerializer(movie_sessions, many=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_movie_sessions_list_with_filter_by_movie(self):
        response = self.client.get(MOVIE_SESSION_LIST_URL, {"movie": "1"})
        movie_sessions = self.movie_sessions_list.filter(movie_id=1)
        serializer = MovieSessionListSerializer(movie_sessions, many=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_movie_sessions_retrive(self):
        id = 1
        response = self.client.get(MOVIE_SESSION_LIST_URL + f"{id}/")
        m_session = MovieSession.objects.get(id=id)
        serializer = MovieSessionDetailSerializer(m_session)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_try_to_create_movie_session(self):
        payload = {
            "show_time": "2024-10-12 13:00:00",
            "movie": 1,
            "cinema_hall": 1,
        }
        response = self.client.post(MOVIE_SESSION_LIST_URL, data=payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_try_to_update_movie_session(self):
        payload = {
            "show_time": "2024-10-12T13:00:00Z",
            "movie": 2,
            "cinema_hall": 2,
        }
        id = 1
        response = self.client.put((MOVIE_SESSION_LIST_URL + f"{id}/"), data=payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_patial_update_movie_session(self):
        payload = {
            "movie": 2,
        }
        id = 1
        response = self.client.patch((MOVIE_SESSION_LIST_URL + f"{id}/"), data=payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_movie_session(self):
        id = 1
        response = self.client.delete(MOVIE_SESSION_LIST_URL + f"{id}/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminTest(TestCase):
    def setUp(self):
        sample_movie_sessions()
        self.admin_user = get_user_model().objects.create_user(
            email="test@test.test",
            password="<PASSWORD>",
            is_staff=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin_user)
        self.movie_sessions_list = MovieSession.objects.all().annotate(
            tickets_available=(
                F("cinema_hall__rows") * F("cinema_hall__seats_in_row")
                - Count("tickets")
            )
        )

    def test_movie_sessions_list(self):
        movie_sessions = self.movie_sessions_list
        serializer = MovieSessionListSerializer(movie_sessions, many=True)
        response = self.client.get(MOVIE_SESSION_LIST_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_movie_sessions_list_with_filter_by_date(self):
        response = self.client.get(MOVIE_SESSION_LIST_URL, {"date": "2024-10-09"})
        movie_sessions = self.movie_sessions_list.filter(show_time__date="2024-10-09")
        serializer = MovieSessionListSerializer(movie_sessions, many=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_movie_sessions_list_with_filter_by_movie(self):
        response = self.client.get(MOVIE_SESSION_LIST_URL, {"movie": "1"})
        movie_sessions = self.movie_sessions_list.filter(movie_id=1)
        serializer = MovieSessionListSerializer(movie_sessions, many=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_movie_sessions_retrive(self):
        id = 1
        response = self.client.get(MOVIE_SESSION_LIST_URL + f"{id}/")
        m_session = MovieSession.objects.get(id=id)
        serializer = MovieSessionDetailSerializer(m_session)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_create_movie_session(self):
        payload = {
            "show_time": "2024-10-12T13:00:00Z",
            "movie": 1,
            "cinema_hall": 1,
        }
        response = self.client.post(MOVIE_SESSION_LIST_URL, data=payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        for key in payload.keys():
            self.assertEqual(payload[key], response.data.get(key))

    def test_update_movie_session(self):
        payload = {
            "show_time": "2024-10-12T13:00:00Z",
            "movie": 2,
            "cinema_hall": 2,
        }
        id = 1
        response = self.client.put((MOVIE_SESSION_LIST_URL + f"{id}/"), data=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for key in payload.keys():
            self.assertEqual(payload[key], response.data.get(key))

    def test_patial_update_movie_session(self):
        payload = {
            "movie": 2,
        }
        id = 1
        response = self.client.patch((MOVIE_SESSION_LIST_URL + f"{id}/"), data=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(payload["movie"], response.data.get("movie"))

    def test_delete_movie_session(self):
        id = 1
        response = self.client.delete(MOVIE_SESSION_LIST_URL + f"{id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
