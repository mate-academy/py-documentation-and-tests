from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.reverse import reverse
from django.test import TestCase
from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_LIST_URL = reverse("cinema:movie-list")


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


def sample_movie(**params):
    defaults = {
        "title": "Test Movie",
        "description": "Test Movie Description",
        "duration": 60,
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)


def sample_actor(**params):
    defaults = {
        "first_name": "Fname",
        "last_name": "Lname",
    }
    defaults.update(params)
    return Actor.objects.create(**defaults)


def sample_genre(**params):
    defaults = {
        "name": "Test Genre",
    }
    defaults.update(params)
    return Genre.objects.create(**defaults)


class UnauthenticatedMovieListAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def detail_movie_url(self, movie_id):
        return reverse("cinema:movie-detail", args=[movie_id])

    def test_unauthenticated_movie_list(self):
        response = self.client.get(MOVIE_LIST_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_movie_retrieve(self):
        cinema = sample_movie()
        url = self.detail_movie_url(cinema.pk)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieListAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com",
            password="test_password",
        )
        self.client.force_authenticate(self.user)

    def test_movie_list(self):
        movie = sample_movie()
        actor = sample_actor(first_name="Robert", last_name="Downey Jr.")
        genre = sample_genre(name="Action")
        movie.genres.add(genre)
        movie.actors.add(actor)
        response = self.client.get(MOVIE_LIST_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_filter_movie_by_title(self):
        movie = sample_movie()
        movie1 = sample_movie(
            title="Movie2",
            description="Movie Description",
            duration=110,
        )
        response = self.client.get(MOVIE_LIST_URL, {f"title": movie.title})
        serializer_movie = MovieListSerializer(movie)
        serializer_movie1 = MovieListSerializer(movie1)
        self.assertIn(serializer_movie.data, response.data)
        self.assertNotIn(serializer_movie1.data, response.data)

    def test_filter_movie_by_genre(self):
        movie = sample_movie(
            title="Movie",
        )
        movie1 = sample_movie(
            title="Movie1",
        )
        genre = sample_genre(name="Action")
        movie.genres.add(genre)
        serializer_with_genre = MovieListSerializer(movie)
        serializer_without_genre = MovieListSerializer(movie1)
        response = self.client.get(MOVIE_LIST_URL, {f"genres": genre.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(serializer_with_genre.data, response.data)
        self.assertNotIn(serializer_without_genre.data, response.data)

    def test_filter_movie_by_actor(self):
        movie = sample_movie()
        movie1 = sample_movie()
        actor = sample_actor(first_name="Igor", last_name="Omlet")
        movie.actors.add(actor)
        serializer_with_actor = MovieListSerializer(movie)
        serializer_without_actor = MovieListSerializer(movie1)
        response = self.client.get(MOVIE_LIST_URL, {f"actors": actor.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(serializer_with_actor.data, response.data)
        self.assertNotIn(serializer_without_actor.data, response.data)

    def test_movie_retrieve(self):
        movie = sample_movie()
        movie_url = detail_url(movie.id)
        response = self.client.get(movie_url)
        serializer = MovieDetailSerializer(movie)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_create_movie_forbidden(self):
        response = self.client.post(
            MOVIE_LIST_URL,
            {
                "title": "Test Movie",
                "description": "Test Movie Description",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdmiCinemaTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com",
            password="PASSWORD",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        data = {
            "title": "Test Movie",
            "description": "Test Movie Description",
            "duration": 110,
        }
        response = self.client.post(MOVIE_LIST_URL, data)
        movie = Movie.objects.get(id=response.data["id"])
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        for key in data:
            self.assertEqual(data[key], getattr(movie, key))

    def test_create_movie_with_genre(self):
        genre = sample_genre(name="Action")
        data = {
            "title": "Test Movie",
            "description": "Test Movie Description",
            "duration": 110,
            "genres": [genre.id],
        }
        response = self.client.post(MOVIE_LIST_URL, data)
        movie = Movie.objects.get(id=response.data["id"])
        genres = movie.genres.all()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(genres.count(), 1)
        self.assertIn(genre, genres)
