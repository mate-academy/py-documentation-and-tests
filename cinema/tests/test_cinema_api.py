import pytest
from django.contrib.auth import get_user, get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient, APITestCase

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer
from cinema.tests.test_movie_api import sample_genre, sample_actor

MOVIE_URL = reverse("cinema:movie-list")


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


class UnauthenticationCinemaApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_movie_unauthorized_fails(self):
        payload = {
            "title": "Unauthorized Movie",
            "description": "Should not be created",
            "duration": 100,
        }
        res = self.client.post(MOVIE_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticationCinemaApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com",
            password="testpassword",
        )
        self.client.force_authenticate(self.user)

    def test_movie_list(self):
        movie = Movie.objects.create(
            title="Example Movie", description="Example description", duration=120
        )
        movie.genres.add(Genre.objects.create(name="Test genre"))
        movie.actors.add(Actor.objects.create(first_name="Test"))

        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_movie_detail(self):
        movie = Movie.objects.create(
            title="Example Movie", description="Example description", duration=120
        )

        url = detail_url(movie.id)
        res = self.client.get(url)
        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_title(self):
        Movie.objects.create(
            title="Example Movie",
            description="Example description",
            duration=120,
        )

        res = self.client.get(MOVIE_URL, {"title": "Test title"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_filter_movies_by_genre(self):
        Movie.objects.create(
            title="Example Movie",
            description="Example description",
            duration=120,
        )

        res = self.client.get(MOVIE_URL, {"genre": "Test genre"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)

    def test_filter_movies_by_actor(self):
        Movie.objects.create(
            title="Example Movie",
            description="Example description",
            duration=120,
        )

        res = self.client.get(MOVIE_URL, {"actor": "Test actor"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
