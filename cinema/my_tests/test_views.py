from unittest import TestCase

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie
from cinema.serializers import MovieDetailSerializer, MovieSerializer

MOVIE_URL = reverse("cinema:movie-list")


def create_movie(**params) -> Movie:
    movie = {
        "title": "Test",
        "description": "Test description",
        "duration": 11,
    }
    movie.update(params)
    return Movie.objects.create(**movie)


def movie_detail(movie_id: int) -> str:
    detail_url = reverse("cinema:movie-detail", args=movie_id)
    return detail_url


class PublicMovieViewSetTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_anon_can_not_visit_page(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateMovieViewSetTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "us1er@test.com",
            "passwordtest123"
        )
        self.client.force_authenticate(self.user)

    def test_user_can_list_movies(self):
        create_movie()
        create_movie()

        movies = Movie.objects.all()
        serializer = MovieSerializer(movies, many=True)
        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_user_can_retrieve_movie(self):
        movie = create_movie()
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.data, movie)

    def test_user_can_not_create_movie(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_can_not_destroy_movie(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_can_not_particular_update_movie(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_can_not_update_movie(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AdminMovieViewSetTests(TestCase):
    def setUp(self) -> None:
        pass
