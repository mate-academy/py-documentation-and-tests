from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from cinema.models import Movie, Actor, Genre
from cinema.serializers import MovieListSerializer

MOVIE_URL = reverse("cinema:movie-list")


def movie_detail_url(movie_id):
    return reverse("cinema:movie-detail", args=(movie_id,))


def sample_movie(**param) -> Movie:
    defaults = {
        "title": "test movie title",
        "description": "test movie description",
        "duration": 182
    }
    defaults.update(param)
    return Movie.objects.create(**defaults)


def sample_actor(**param) -> Actor:
    defaults = {
        "first_name": "John",
        "last_name": "Smith"
    }
    defaults.update(param)
    return Actor.objects.create(**defaults)


def sample_genre(**param) -> Genre:
    defaults = {
        "name": "horror",

    }
    defaults.update(param)
    return Genre.objects.create(**defaults)


class UnauthenticatedMovieTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        result = self.client.get(MOVIE_URL)
        self.assertEqual(result.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieSessionTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email='test_user@gmail.com',
            password="HSDKG&@NV8"
        )

        self.ironman_movie = sample_movie(title="ironman")
        self.hancock = sample_movie(title="Hancock")

        self.default_movie = sample_movie(title="Test_movie")

        self.actor_1 = sample_actor(first_name="Robert", last_name="Downey")
        self.actor_2 = sample_actor(first_name="Will", last_name="Smith")
        self.actor_3 = sample_actor(first_name="Marie", last_name="Norman")
        self.genre_1 = sample_genre(name="fantastic")
        self.genre_2 = sample_genre(name="comedy")

        self.ironman_movie.actors.add(self.actor_1)
        self.ironman_movie.genres.add(self.genre_1)

        self.hancock.actors.add(self.actor_2, self.actor_2)
        self.hancock.genres.add(self.genre_1, self.genre_2)

        self.client.force_authenticate(self.user)

    def test_movie_list(self):
        sample_movie()
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)
        result = self.client.get(MOVIE_URL)
        self.assertEqual(result.data, serializer.data)

    def test_movie_list_filtered_by_title(self):
        result = self.client.get(MOVIE_URL, {"title": 'ironman'})

        movie_serializer1 = MovieListSerializer(self.ironman_movie)
        movie_serializer2 = MovieListSerializer(self.hancock)

        self.assertIn(movie_serializer1.data, result.data)
        self.assertNotIn(movie_serializer2.data, result.data)

    def test_movie_list_filtered_by_actor_id(self):
        result = self.client.get(MOVIE_URL, {"actors": self.actor_1.id})

        movie_serializer1 = MovieListSerializer(self.ironman_movie)
        movie_serializer2 = MovieListSerializer(self.hancock)
        movie_serializer3 = MovieListSerializer(self.default_movie)

        self.assertIn(movie_serializer1.data, result.data)
        self.assertNotIn(movie_serializer2.data, result.data)
        self.assertNotIn(movie_serializer3.data, result.data)

    def test_movie_list_filtered_by_genre_id(self):
        result = self.client.get(MOVIE_URL, {"genres": self.genre_2.id})

        movie_serializer1 = MovieListSerializer(self.ironman_movie)
        movie_serializer2 = MovieListSerializer(self.hancock)
        movie_serializer3 = MovieListSerializer(self.default_movie)

        self.assertNotIn(movie_serializer1.data, result.data)
        self.assertIn(movie_serializer2.data, result.data)
        self.assertNotIn(movie_serializer3.data, result.data)

    def test_create_movie_access(self):
        movie = {
            "title": "test_movie",
            "description": "test_description",
            "duration": 154,
        }

        result = self.client.post(MOVIE_URL, movie)
        self.assertEqual(result.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = get_user_model().objects.create_user(
            email="admin@mail.ua",
            password="testQwery2134",
            is_staff=True,
        )

        self.movie_test = sample_movie(title="test_movie")
        self.genre_test = sample_genre(name="test_genre")
        self.actor_test = sample_actor(first_name="Test", last_name="User")

        self.client.force_authenticate(user=self.admin)

    def test_create_movie(self):
        movie = {
            "title": "test_movie",
            "description": "test description",
            "duration": 154,
            "actors": self.genre_test.id,
            "genres": self.actor_test.id
        }

        result = self.client.post(MOVIE_URL, movie)
        self.assertEqual(result.status_code, status.HTTP_201_CREATED)

    def test_delete_movie(self):
        result = self.client.delete(
            reverse(
                "cinema:movie-detail",
                args=(self.movie_test.id,)
            )
        )
        self.assertEqual(result.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
