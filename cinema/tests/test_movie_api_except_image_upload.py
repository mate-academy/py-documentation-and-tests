from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import Movie
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_LIST_URL = reverse("cinema:movie-list")
MOVIE_DETAIL_URL = reverse("cinema:movie-detail", kwargs={"pk": 1})


class UnauthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(MOVIE_LIST_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    fixtures = ["cinema_service_db_data.json"]

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.get(pk=2)
        self.client.force_authenticate(self.user)

    def test_movie_list(self):
        response = self.client.get(MOVIE_LIST_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_movie_list_with_filters(self):
        response = self.client.get(
            MOVIE_LIST_URL,
            {
                "title": "Departed",
                "genres": "1",
                "actors": "1",
            }
        )
        movies = Movie.objects.filter(
            title__contains="Departed",
            genres__id__in=[1],
            actors__id__in=[1],
        )
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)
        
    def test_movie_retrieve(self):
        response = self.client.get(MOVIE_DETAIL_URL)
        movie = Movie.objects.get(pk=1)
        serializer = MovieDetailSerializer(movie)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_create_forbidden(self):
        response = self.client.post(
            MOVIE_LIST_URL,
            {
                "title": "Test_title",
                "description": "Test_description",
                "duration": 100,
                "genres": [1],
                "actors": [1],
            }
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTests(TestCase):
    fixtures = ["cinema_service_db_data.json"]

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.get(pk=1)
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        data = {
            "title": "Test_title",
            "description": "Test_description",
            "duration": 100,
            "genres": [1],
            "actors": [1],
        }
        response = self.client.post(
            MOVIE_LIST_URL,
            data=data
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        test_movie = Movie.objects.get(pk=response.data["id"])
        self.assertEqual(data["title"], test_movie.title)
        self.assertEqual(data["description"], test_movie.description)
        self.assertEqual(data["duration"], test_movie.duration)
        self.assertEqual(data["genres"], [genre.id for genre in test_movie.genres.all()])
        self.assertEqual(data["actors"], [actor.id for actor in test_movie.actors.all()])

    def test_delete_not_allowed(self):
        response = self.client.delete(MOVIE_DETAIL_URL)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_update_not_allowed(self):
        data = {
            "title": "Test_title",
            "description": "Test_description",
            "duration": 100,
            "genres": [1],
            "actors": [1],
        }
        response = self.client.put(MOVIE_DETAIL_URL, data=data)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_partial_update_not_allowed(self):
        data = {
            "title": "Test_title",
        }
        response = self.client.patch(MOVIE_DETAIL_URL, data=data)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
