from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")

def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=(movie_id,))

def sample_movie(**params) -> Movie:
    defaults = {
        "title": "Test_Movie",
        "description": "Test_Movie description",
        "duration": 45,
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)


class UnauthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="testmail@email.com", password="test_password"
        )
        self.client.force_authenticate(self.user)

    def test_movies_list(self):
        sample_movie()

        movie_with_genres = sample_movie(title="Movie with genres")
        genre_1 = Genre.objects.create(name="Thriller")
        genre_2 = Genre.objects.create(name="Fantasy")
        movie_with_genres.genres.add(genre_1, genre_2)

        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_genres(self):
        movie_without_genres = sample_movie(title="Movie without genres")
        movie_with_genre_1 = sample_movie(title="Thriller movie")
        movie_with_genre_2 = sample_movie(title="Fantasy movie")

        genre_1 = Genre.objects.create(name="Thriller")
        genre_2 = Genre.objects.create(name="Fantasy")

        movie_with_genre_1.genres.add(genre_1)
        movie_with_genre_2.genres.add(genre_2)

        res = self.client.get(
            MOVIE_URL,
            {"genres": f"{genre_1.id}, {genre_2.id}"},
        )

        serializer_without_genres = MovieListSerializer(movie_without_genres)
        serializer_with_genre_1 = MovieListSerializer(movie_with_genre_1)
        serializer_with_genre_2 = MovieListSerializer(movie_with_genre_2)

        self.assertIn(serializer_with_genre_1.data, res.data)
        self.assertIn(serializer_with_genre_2.data, res.data)
        self.assertNotIn(serializer_without_genres.data, res.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        movie.genres.add(Genre.objects.create(name="Art-house"))

        url = detail_url(movie.id)
        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Test movie",
            "description": "Test Movie description",
            "duration": 45,
        }

        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@email.com", password="admin_password", is_staff=True
        )
        self.client.force_authenticate(user=self.user)

    def test_create_movie(self):
        payload = {
            "title": "Test movie",
            "description": "Test Movie description",
            "duration": 45,
        }
        res = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_create_movie_with_genres(self):
        genre_1 = Genre.objects.create(name="Thriller")
        genre_2 = Genre.objects.create(name="Fantasy")
        payload = {
            "title": "Test movie",
            "description": "Test Movie description",
            "duration": 45,
            "genres": [genre_1.id, genre_2.id]
        }
        res = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(id=res.data["id"])
        genres = movie.genres.all()
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn(genre_1, genres)
        self.assertIn(genre_2, genres)
        self.assertEqual(genres.count(), 2)

    def test_delete_movie_not_allowed(self):
        movie = sample_movie()
        url = detail_url(movie.id)

        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
