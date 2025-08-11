from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import CinemaHall, MovieSession, Movie
from cinema.serializers import (
    MovieSessionListSerializer,
    MovieSessionSerializer,
    MovieSessionDetailSerializer
)


class UnauthenticatedMovieSessionApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(reverse("cinema:moviesession-list"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieSessionApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com",
            password="testPass1"
        )
        self.client.force_authenticate(user=self.user)
        self.movie = Movie.objects.create(
            title="test",
            description="test",
            duration=80
        )
        self.theater_hall = CinemaHall.objects.create(
            name="test",
            rows=5,
            seats_in_row=5
        )
        self.movie_session = MovieSession.objects.create(
            show_time="2024-04-07T11:45:12.009Z",
            movie=self.movie,
            cinema_hall=self.theater_hall
        )

    def test_movie_session_list(self):
        response = self.client.get(reverse("cinema:moviesession-list"))
        cinema_halls = MovieSession.objects.all()
        serializer = MovieSessionListSerializer(cinema_halls, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), len(serializer.data))

    def test_movie_session_detail(self):
        response = self.client.get(reverse(
            "cinema:moviesession-detail",
            kwargs={"pk": self.movie.id}
        ))
        movie_session = MovieSession.objects.get(pk=self.movie.id)
        serializer = MovieSessionDetailSerializer(movie_session)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_admin_rights_required(self):
        data = {
            "first_name": "John",
            "last_name": "Doe"
        }
        response = self.client.post(reverse("cinema:genre-list"), data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieSessionApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            email="admin@admin.com",
            password="adminPass1"
        )
        self.client.force_authenticate(user=self.user)
        self.movie = Movie.objects.create(
            title="test",
            description="test",
            duration=80,
        )
        self.theater_hall = CinemaHall.objects.create(
            name="test",
            rows=5,
            seats_in_row=5
        )
        self.movie_session = MovieSession.objects.create(
            movie=self.movie,
            cinema_hall=self.theater_hall,
            show_time="2024-04-07T11:45:12.009Z"
        )

    def test_movie_session_create(self):
        data = {
            "show_time": "2024-04-07T11:45:12.009Z",
            "movie": self.movie.id,
            "cinema_hall": self.theater_hall.id
        }
        response = self.client.post(
            reverse("cinema:moviesession-list"),
            data
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        movie_session = MovieSession.objects.get(id=response.data["id"])
        serializer = MovieSessionSerializer(movie_session)
        self.assertEqual(response.data, serializer.data)

    def test_movie_session_create_with_invalid_data(self):
        data = {
            "show_time": "invalid data",
            "movie": "invalid data",
            "cinema_hall": "invalid data"
        }
        response = self.client.post(
            reverse("cinema:moviesession-list"),
            data
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_movie_session_update(self):
        data = {
            "show_time": "2025-12-07T13:14:06.502Z",
            "movie": 1,
            "cinema_hall": 1
        }
        response = self.client.put(
            reverse(
                "cinema:moviesession-detail",
                kwargs={"pk": self.movie_session.id}
            ),
            data
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        movie_session = MovieSession.objects.get(id=response.data["id"])
        serializer = MovieSessionSerializer(movie_session)
        self.assertEqual(response.data, serializer.data)

    def test_movie_session_partial_update(self):
        data = {
            "show_time": "2025-01-01T13:14:06.502Z",
        }
        response = self.client.patch(
            reverse(
                "cinema:moviesession-detail",
                kwargs={"pk": self.movie_session.id}
            ),
            data
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        movie_session = MovieSession.objects.get(id=response.data["id"])
        serializer = MovieSessionSerializer(movie_session)
        self.assertEqual(response.data, serializer.data)

    def test_movie_session_delete(self):
        response = self.client.delete(
            reverse("cinema:moviesession-detail", kwargs={"pk": self.movie_session.id})
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(MovieSession.objects.count(), 0)
