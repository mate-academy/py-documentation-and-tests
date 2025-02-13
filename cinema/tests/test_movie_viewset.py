from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from cinema.models import Movie, Genre
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")


def detail_url(movie_id: int):
    return reverse("cinema:movie-detail", args=(movie_id,))


def sample_movie(**params) -> Movie:
    default = {
        "title": "Test movie",
        "description": "Test movie description",
        "duration": 30
    }
    default.update(params)
    return Movie.objects.create(**default)


class UnauthenticatedMovieTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com", password="test"
        )
        self.client.force_authenticate(self.user)

    def test_movie_list(self):
        sample_movie()
        movie_with_genres = sample_movie(title="Test movie with genres")
        genre_1 = Genre.objects.create(name="Drama")
        genre_2 = Genre.objects.create(name="Comedy")
        movie_with_genres.genres.add(genre_1, genre_2)

        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"], serializer.data)

    def test_filter_buses_by_facilities(self):
        movie_without_genre = sample_movie()
        movie_with_genre = sample_movie(title="Genre test movie")
        genre = Genre.objects.create(name="Drama")

        movie_with_genre.genres.add(genre)

        res = self.client.get(
            MOVIE_URL,
            {"genres": f"{genre.id}"}
        )

        serializer_without_genre = MovieListSerializer(movie_without_genre)
        serializer_with_genre = MovieListSerializer(movie_with_genre)

        self.assertIn(serializer_with_genre.data, res.data["results"])
        self.assertNotIn(serializer_without_genre.data, res.data["results"])

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        movie.genres.add(Genre.objects.create(name="Drama"))

        url = detail_url(movie.id)

        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Test movie forbidden",
            "description": "Test movie description",
            "duration": 30
        }
        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@test.com", password="test", is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        payload = {
            "title": "Test movie admin create",
            "description": "Test movie description",
            "duration": 30
        }
        res = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_delete_movie_not_allowed(self):
        movie = sample_movie()
        url = detail_url(movie.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
