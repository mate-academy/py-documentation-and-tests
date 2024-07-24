from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.reverse import reverse
from django.test import TestCase
from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer


MOVIE_URL = reverse("cinema:movie-list")


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


class UnauthenticatedMovieApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@gmail.com",
            "testpassword123"
        )
        self.client.force_authenticate(self.user)

    def test_movie_list(self):
        movie = sample_movie()
        actor = sample_actor(first_name="Lili", last_name="Down")
        genre = sample_genre(name="Drama")
        movie.actors.add(actor)
        movie.genres.add(genre)
        response = self.client.get(MOVIE_URL)
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
        response = self.client.get(MOVIE_URL, {f"title": movie.title})
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
        genre = sample_genre(name="Drama")
        movie.genres.add(genre)
        serializer_with_genre = MovieListSerializer(movie)
        serializer_without_genre = MovieListSerializer(movie1)
        response = self.client.get(MOVIE_URL, {f"genres": genre.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(serializer_with_genre.data, response.data)
        self.assertNotIn(serializer_without_genre.data, response.data)

    def test_filter_movie_by_actor(self):
        movie = sample_movie()
        movie1 = sample_movie()
        actor = sample_actor(first_name="Olia", last_name="Kim")
        movie.actors.add(actor)
        serializer_with_actor = MovieListSerializer(movie)
        serializer_without_actor = MovieListSerializer(movie1)
        response = self.client.get(MOVIE_URL, {f"actors": actor.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(serializer_with_actor.data, response.data)
        self.assertNotIn(serializer_without_actor.data, response.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        movie.actors.add(sample_actor(first_name="Olia", last_name="Kim"))
        url = detail_url(movie.id)
        response = self.client.get(url)
        serializer = MovieDetailSerializer(movie)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Test Movie",
            "description": "Test Movie Description"
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@gmail.com",
            password="testpassword123",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        payload = {
            "title": "Test Movie",
            "description": "Test Movie Description",
            "duration": 110,
        }
        res = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(pk=res.data["id"])
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_create_movie_genre(self):
        genre = sample_genre(name="Drama")
        payload = {
            "title": "Test Movie",
            "description": "Test Movie Description",
            "duration": 110,
            "genres": [genre.id],
        }
        res = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(pk=res.data["id"])
        genres = movie.genres.all()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(genres.count(), 1)
        self.assertIn(genre, genres)

    def test_delete_movie_not_allowed(self):
        movie = sample_movie()
        url = detail_url(movie.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
