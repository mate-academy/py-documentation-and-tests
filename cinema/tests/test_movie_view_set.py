from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.request import Request
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from cinema.models import Movie, Genre
from cinema.serializers import (MovieListSerializer,
                                MovieDetailSerializer)

MOVIE_URL = reverse("cinema:movie-list")


def sample_movie(**params) -> Movie:
    defaults = {
        "title": "Inception",
        "description": "Movie for movie",
        "duration": 123,
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)

def detail_url(movie_id: int) -> Request:
    return reverse("cinema:movie-detail", args=(movie_id,))


class UnauthorizedMovieApiTests(TestCase):

    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self) -> None:
        result = self.client.get(MOVIE_URL)
        self.assertEqual(result.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthorizedMovieApiTests(TestCase):

    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test9@email.test",
            "testpass",
        )
        self.client.force_authenticate(user=self.user)

    def test_movie_list(self) -> None:
        sample_movie()

        movie_new_genre = sample_movie()

        genre_ = Genre.objects.create(name="historical")

        movie_new_genre.genres.add(genre_)

        result = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(result.status_code, status.HTTP_200_OK)
        self.assertEqual(result.data, serializer.data)

    def test_filter_movies_by_title(self) -> None:
        movie_one = sample_movie(title="DeadPool")
        movie_two = sample_movie(title="Terminator")

        result = self.client.get(
            MOVIE_URL, {"title": "DeadPool"}
        )
        serializer_movie_one = MovieListSerializer(movie_one)
        serializer_movie_two = MovieListSerializer(movie_two)

        self.assertIn(serializer_movie_one.data, result.data)
        self.assertNotIn(serializer_movie_two.data, result.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        movie.genres.add(Genre.objects.create(name="Cartoon"))

        url = detail_url(movie.id)

        result = self.client.get(url)
        serializer = MovieDetailSerializer(movie)
        self.assertEqual(result.status_code, status.HTTP_200_OK)
        self.assertEqual(result.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Terminator",
            "description": "I ll be back",
            "duration": 333,
        }

        result = self.client.post(MOVIE_URL, payload)

        self.assertEqual(result.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTests(TestCase):

    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin1@email.test",
            password="testpass",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.user)

    def test_create_movie_with_permissions(self):
        payload = {
            "title": "Terminator",
            "description": "I ll be back",
            "duration": 333,
        }

        result = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(id=result.data.get("id"))

        self.assertEqual(result.status_code, status.HTTP_201_CREATED)

        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_create_movie_with_genres(self):
        genre_ = Genre.objects.create(name="drama")
        payload = {
            "title": "Terminator",
            "description": "I ll be back",
            "duration": 333,
            "genres": genre_.id
        }

        result = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(id=result.data.get("id"))
        genres = movie.genres.all()

        self.assertEqual(result.status_code, status.HTTP_201_CREATED)
        self.assertIn(genre_, genres)
        self.assertEqual(genres.count(), 1)
