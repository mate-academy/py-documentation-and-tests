from unittest import TestCase

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import Movie
from cinema.serializers import MovieSerializer

MOVIE_URL = reverse("cinema:movie-list")


def create_movie(**params) -> Movie:
    movie = {
        "title": "Test",
        "description": "Test description",
        "duration": 11,
    }
    movie.update(params)
    return Movie.objects.create(**movie)


class PrivateMovieViewSetTests(TestCase):
    def test_user_can_list_movies(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "us1er@test.com",
            "passwordtest123"
        )
        self.client.force_authenticate(self.user)
        create_movie()
        create_movie()

        movies = Movie.objects.all()
        serializer = MovieSerializer(movies, many=True)
        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)
