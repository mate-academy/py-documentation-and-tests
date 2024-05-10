from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from cinema.serializers import MovieListSerializer, MovieSerializer
from cinema.models import Movie
from .test_movie_api import sample_movie, sample_genre, sample_actor


class TestAuthorisedMovie(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@gmail.com",
            "testpassword123"
        )
        self.client.force_authenticate(self.user)

    def test_movie_list(self) -> None:
        url = reverse("cinema:movie-list")
        res = self.client.get(url)  # get a list of data from url

        items = Movie.objects.all()  # get a list of data from db
        serializer = MovieListSerializer(items, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(serializer.data, res.data)

    def test_movie_filter_by_title(self) -> None:
        movie = sample_movie(title="Inception")
        serializer = MovieListSerializer(movie)
        res = self.client.get(
            reverse("cinema:movie-list"),
            {"title": movie.title}
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        filtered_data = dict(res.data[0])
        self.assertEqual(filtered_data, serializer.data)

    def test_movie_filter_by_genre(self) -> None:
        movie = sample_movie()
        genre = sample_genre()
        movie.genres.set([genre])
        serializer = MovieListSerializer(movie)
        genre_ids = [g.id for g in movie.genres.all()]
        res = self.client.get(
            reverse("cinema:movie-list"),
            {"genres": genre_ids}
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        filtered_data = dict(res.data[0])
        self.assertEqual(filtered_data, serializer.data)

    def test_movie_filter_by_actor(self) -> None:
        movie = sample_movie()
        actor = sample_actor()
        movie.actors.set([actor])
        serializer = MovieListSerializer(movie)
        actor_ids = [a.id for a in movie.actors.all()]
        res = self.client.get(
            reverse("cinema:movie-list"),
            {"actors": actor_ids}
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        filtered_data = dict(res.data[0])
        self.assertEqual(filtered_data, serializer.data)

    def test_create_movie_forbidden(self):
        movie = {
            "title": "Test Movie Title",
            "decription": "Test Movie Description",
            "duration": 60,
        }
        res = self.client.post(
            reverse("cinema:movie-list"),
            data=movie
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class TestUnauthorizedMovieView(TestCase):
    def test_auth_required(self):
        client = APIClient()
        res = client.get(reverse("cinema:movie-list"))
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
