from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from cinema.models import MovieSession
from cinema.serializers import (
    MovieSessionDetailSerializer,
    MovieSessionListSerializer,
)
from cinema.tests.test_base import (
    sample_user,
    sample_movie,
    sample_cinema_hall,
    sample_movie_session,
    sample_admin_user,
)


def get_movie_session_list_url():
    return reverse("cinema:movie_session-list")


def get_movie_session_detail_url(pk: int):
    return reverse("cinema:movie_session-detail", kwargs={"pk": pk})


class UnauthenticatedMovieSessionTests(TestCase):
    def test_auth_required(self):
        self.client = APIClient()
        res = self.client.get(get_movie_session_list_url())

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieSessionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = sample_user()
        self.client.force_authenticate(user=self.user)
        self.movie_session = sample_movie_session()

    def test_movie_session_detail(self):
        res = self.client.get(
            get_movie_session_detail_url(self.movie_session.id)
        )

        serializer = MovieSessionDetailSerializer(
            MovieSession.objects.get(id=self.movie_session.id)
        )

        self.assertEqual(res.data, serializer.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_movie_session_list_filter_by_date(self):
        movie_session_1 = sample_movie_session(show_time="2026-06-02 14:00:00")
        movie_session_2 = sample_movie_session(show_time="2026-06-03 14:00:00")

        res = self.client.get(
            get_movie_session_list_url(), {"date": "2026-06-03"}
        )

        serializer = MovieSessionListSerializer(
            MovieSession.objects.filter(pk=movie_session_2.pk), many=True
        )

        data = [dict(item) for item in res.data]
        for item in data:
            self.assertIn("tickets_available", item)
            item.pop("tickets_available")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(data, serializer.data)

    def test_movie_session_list_filter_by_movie_id(self):
        movie_1 = sample_movie()
        movie_2 = sample_movie()
        movie_session_1 = sample_movie_session(movie=movie_1)
        movie_session_2 = sample_movie_session(movie=movie_2)

        res = self.client.get(
            get_movie_session_list_url(), {"movie": movie_session_2.pk}
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)

    def test_create_movie_session_forbidden(self):
        cinema_hall = sample_cinema_hall()
        movie = sample_movie()

        payload = {
            "show_time": "2022-06-02 14:00:00",
            "cinema_hall": cinema_hall,
            "movie": movie,
        }
        res = self.client.post(get_movie_session_list_url(), payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieSessionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = sample_admin_user()
        self.client.force_authenticate(user=self.user)
        self.movie_session = sample_movie_session()

    def test_create_movie_session(self):
        cinema_hall = sample_cinema_hall()
        movie = sample_movie()

        payload = {
            "show_time": "2022-06-02 14:00:00",
            "cinema_hall": cinema_hall.pk,
            "movie": movie.pk,
        }
        res = self.client.post(get_movie_session_list_url(), payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            MovieSession.objects.filter(pk=res.data["id"]).exists()
        )

    def test_update_movie_session(self):
        cinema_hall = sample_cinema_hall()
        movie = sample_movie(title="MovieOld")
        movie_session = sample_movie_session(
            cinema_hall=cinema_hall, movie=movie
        )

        new_movie = sample_movie(title="MovieNew")
        payload = {
            "show_time": "2022-06-02 14:00:00",
            "cinema_hall": cinema_hall.pk,
            "movie": new_movie.pk,
        }

        res = self.client.put(
            get_movie_session_detail_url(movie_session.id), payload
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["movie"], new_movie.pk)
        movie_session.refresh_from_db()
        self.assertEqual(movie_session.movie.title, new_movie.title)

    def test_delete_movie_session(self):
        res = self.client.delete(
            get_movie_session_detail_url(self.movie_session.id)
        )

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            MovieSession.objects.filter(pk=self.movie_session.pk).exists()
        )
