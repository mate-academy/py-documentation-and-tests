from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, Genre
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")


def detail_url(movie_id): #127.0.0.1/api/cinema/movies/<movie_id>/
    return reverse("cinema:movie-detail", args=(movie_id,))


def sample_movie(**params):
    defaults = {
        "title": "Sample movie",
        "description": "Sample description",
        "duration": 90,
    }
    defaults.update(params)

    return Movie.objects.create(**defaults)

class UnauthenticatedMovieTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.test", password="testpassword"
        )
        self.client.force_authenticate(self.user)


    def test_movies_list(self):
        sample_movie()
        movie_with_genres = sample_movie()
        genre_1 = Genre.objects.create(name="WiFi1")
        genre_2 = Genre.objects.create(name="WiFi2")
        movie_with_genres.genres.add(genre_1, genre_2)
        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_genre(self):
        movie_without_genre = sample_movie()
        movie_with_genre_1 = sample_movie(title="Sample movie1")
        movie_with_genre_2 = sample_movie(title="Sample movie2")

        genre_1 = Genre.objects.create(name="WiFi1")
        genre_2 = Genre.objects.create(name="WiFi2")

        movie_with_genre_1.genres.add(genre_1)
        movie_with_genre_2.genres.add(genre_2)

        res = self.client.get(
            MOVIE_URL,
            {"genres": f"{genre_1.id},{genre_2.id}"}
        )

        serializer_without_genres = MovieListSerializer(movie_without_genre)
        serializer_movi_genre_1 = MovieListSerializer(movie_with_genre_1)
        serializer_movi_genre_2 = MovieListSerializer(movie_with_genre_2)

        self.assertIn(serializer_movi_genre_1.data, res.data)
        self.assertIn(serializer_movi_genre_2.data, res.data)
        self.assertNotIn(serializer_without_genres, res.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        movie.genres.add(Genre.objects.create(name="WiFi3"))

        url = detail_url(movie.id)
        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
             "title": "Sample",
             "description": "Sfff",
             "duration": 90
        }

        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

class AdminMovieTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@admin.test", password="testpassword", is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_movies(self):
        payload = {"title": "Sample1", "description": "Sfff", "duration": 20}
        res = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_create_movies_with_genres(self):
        genre_1 = Genre.objects.create(name="WiFi16")
        genre_2 = Genre.objects.create(name="WiFi52")
        
        payload = {"title": "Sample1", "description": "Sfff", "duration": 20, "genres": [genre_1.id, genre_2.id]}
        
        res = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(id=res.data["id"])
        genres = Genre.objects.all()
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn(genre_1, genres)
        self.assertIn(genre_2, genres)
        self.assertEqual(genres.count(), 2)

    def test_delete_movie_not_allowed(self):
        movie = sample_movie()
        url = detail_url(movie.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        