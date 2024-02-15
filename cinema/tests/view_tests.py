from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer

MOVIE_URL = reverse("cinema:movie-list")


class MovieViewSetTests(TestCase):
    def setUp(self) -> None:
        self.non_user_client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@gmail.com",
            "test_password",
        )
        self.user_client = APIClient()
        self.user_client.force_authenticate(user=self.user)
        self.movie1 = Movie.objects.create(
            title="Test Movie 1",
            duration=99,
        )
        self.movie2 = Movie.objects.create(
            title="Test Movie 2",
            duration=66,
        )
        self.test_genre = Genre.objects.create(name="Test Genre")
        self.movie2.genres.add(
            self.test_genre,
        )
        self.genre_response = self.user_client.get(
            MOVIE_URL, {"genres": self.test_genre.id}
        )
        self.response = self.user_client.get(MOVIE_URL)
        self.detail_response = self.user_client.get(f"{MOVIE_URL}{self.movie1.pk}/")
        self.serializer = MovieListSerializer(Movie.objects.all(), many=True)

    def test_non_user_auth_required(self):
        self.assertEqual(
            self.non_user_client.get(MOVIE_URL).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_list_movies_status(self):
        self.assertEqual(
            self.response.status_code,
            status.HTTP_200_OK,
        )

    def test_list_movies_count(self):
        self.assertEqual(
            len(self.response.data),
            2,
        )

    def test_retrieve_movie_status(self):
        self.assertEqual(
            self.detail_response.status_code,
            status.HTTP_200_OK,
        )

    def test_retrieve_movie_title(self):
        self.assertEqual(
            self.detail_response.data["title"],
            "Test Movie 1",
        )

    def test_serializer(self):
        self.assertEqual(
            self.response.data,
            self.serializer.data,
        )

    def test_filter_by_genres_status(self):
        self.assertEqual(
            self.genre_response.status_code,
            status.HTTP_200_OK,
        )

    def test_filter_by_genres_count(self):
        self.assertEqual(
            len(self.genre_response.data),
            1,
        )

    def test_filter_by_actors(self):
        test_actor = Actor.objects.create()
        self.movie1.actors.add(test_actor)
        response = self.user_client.get(MOVIE_URL, {"actors": test_actor.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_create_movie_forbidden(self):
        self.assertEqual(
            self.user_client.post(
                MOVIE_URL,
                {"title": "Test Movie", "description": "Movie create forbidden"},
            ).status_code,
            status.HTTP_403_FORBIDDEN,
        )
