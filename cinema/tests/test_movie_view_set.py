from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from cinema.models import Movie, CinemaHall, Genre, Actor
from cinema.serializers import (
    MovieListSerializer,
    MovieDetailSerializer,
    MovieImageSerializer,
    MovieSerializer,
)
from cinema.views import MovieViewSet

MOVIE_URL = reverse("cinema:movie-list")
MOVIE_SESSION_URL = reverse("cinema:moviesession-list")


def sample_movie(**params):
    defaults = {
        "title": "Sample movie",
        "description": "Sample description",
        "duration": 90,
    }
    defaults.update(params)

    return Movie.objects.create(**defaults)


def sample_genre(**params):
    defaults = {
        "name": "Drama",
    }
    defaults.update(params)

    return Genre.objects.create(**defaults)


def sample_actor(**params):
    defaults = {"first_name": "George", "last_name": "Clooney"}
    defaults.update(params)

    return Actor.objects.create(**defaults)


def sample_movie_session(**params):
    cinema_hall = CinemaHall.objects.create(name="Blue", rows=20, seats_in_row=20)

    defaults = {
        "show_time": "2022-06-02 14:00:00",
        "movie": None,
        "cinema_hall": cinema_hall,
    }
    defaults.update(params)


class MovieViewSetTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.test", password="testpassword"
        )
        self.client.force_authenticate(self.user)
        self.genre = sample_genre()
        self.actor = sample_actor()
        self.movie = sample_movie()
        self.movie.genres.add(self.genre)
        self.movie.actors.add(self.actor)
        self.movie.save()

    def test_list_movies(self):
        url = (MOVIE_URL)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_movie(self):
        url = reverse("cinema:movie-detail", args=[self.movie.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_filter_movies_by_title(self):
        url = (MOVIE_URL) + f"?title={self.movie.title}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], self.movie.title)
        self.assertIsNot(response.data[0]["title"], [])

    def test_filter_movies_by_genre(self):
        url = (MOVIE_URL) + f"?genres={self.genre.id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], self.movie.title)
        self.assertIsNot(response.data[0]["genres"], [])

    def test_filter_movies_by_actor(self):
        url = (MOVIE_URL + f"?actors={self.actor.id}")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], self.movie.title)
        self.assertIsNot(response.data[0]["actors"], [])

    def test_get_serializer_class(self):
        view = MovieViewSet()
        view.action = "list"
        self.assertEqual(view.get_serializer_class(), MovieListSerializer)

        view.action = "retrieve"
        self.assertEqual(view.get_serializer_class(), MovieDetailSerializer)

        view.action = "upload_image"
        self.assertEqual(view.get_serializer_class(), MovieImageSerializer)

        view.action = ""
        self.assertEqual(view.get_serializer_class(), MovieSerializer)
