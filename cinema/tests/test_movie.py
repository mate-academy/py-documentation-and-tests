from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer


MOVIE_URL = reverse("cinema:movie-list")

def _sample_movie(**params) -> Movie:
    defaults = {
        "title": "Sample Movie",
        "description": "Some description",
        "duration": 120,
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)


def detail_movie_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


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
            email="user@test.com",
            password="test1234",
        )
        self.client.force_authenticate(self.user)

    def test_movie_list(self):
        _sample_movie()

        movie_with_title = _sample_movie()
        movie_with_genres = _sample_movie()
        movie_with_actors = _sample_movie()

        genres_1 = Genre.objects.create(name="test1")
        genres_2 = Genre.objects.create(name="test2")

        actor_1 = Actor.objects.create(
            first_name="test1",
            last_name="qwerty1"
        )
        actor_2 = Actor.objects.create(
            first_name="test2",
            last_name="qwerty2"
        )

        movie_with_genres.genres.add(genres_1, genres_2)
        movie_with_actors.actors.add(actor_1, actor_2)

        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        res_data_without_image = [{k: v for k, v in movie.items() if k != "image"} for movie in res.data]
        serializer_data_without_image = [{k: v for k, v in movie.items() if k != "image"} for movie in serializer.data]

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res_data_without_image, serializer_data_without_image)

    def test_movie_filter_genres(self):
        movie_without_genres = _sample_movie()
        movie_with_genres1 = _sample_movie()
        movie_with_genres2 = _sample_movie()

        genres_1 = Genre.objects.create(name="test2")
        genres_2 = Genre.objects.create(name="test3")

        movie_with_genres1.genres.add(genres_1)
        movie_with_genres2.genres.add(genres_2)

        res = self.client.get(
            MOVIE_URL,
            {"genres": f"{genres_1.id},{genres_2.id}"}
        )

        serializer_without_genres = MovieListSerializer(movie_without_genres)
        serializer_movie_genres1 = MovieListSerializer(movie_with_genres1)
        serializer_movie_genres2 = MovieListSerializer(movie_with_genres2)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertNotIn(serializer_without_genres.data, res.data)
        self.assertIn(serializer_movie_genres1.data, res.data)
        self.assertIn(serializer_movie_genres2.data, res.data)

    def test_movie_filter_actors(self):
        movie_without_actors = _sample_movie()
        movie_with_actors1 = _sample_movie()
        movie_with_actors2 = _sample_movie()

        actor_1 = Actor.objects.create(
            first_name="test1",
            last_name="qwerty1"
        )
        actor_2 = Actor.objects.create(
            first_name="test2",
            last_name="qwerty2"
        )

        movie_with_actors1.actors.add(actor_1)
        movie_with_actors2.actors.add(actor_2)

        res = self.client.get(
            MOVIE_URL,
            {"actors": f"{actor_1.id},{actor_2.id}"}
        )

        serializer_without_actors = MovieListSerializer(movie_without_actors)
        serializer_with_actor1 = MovieListSerializer(movie_with_actors1)
        serializer_with_actor2 = MovieListSerializer(movie_with_actors2)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertNotIn(serializer_without_actors.data, res.data)
        self.assertIn(serializer_with_actor1.data, res.data)
        self.assertIn(serializer_with_actor2.data, res.data)

    def test_movie_retrieve(self):
        movie = _sample_movie()
        url = detail_movie_url(movie.id)
        res = self.client.get(url)
        serializer = MovieDetailSerializer(movie)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie(self):
        payload = {
            "title": "Sample Movie",
            "description": "Some description",
            "duration": 120,
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@admin.com",
            password="testadmin",
            is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        actor = Actor.objects.create(
            first_name="test1",
            last_name="qwerty1"
        )
        genres = Genre.objects.create(name="test2")
        payload = {
            "title": "Sample Movie",
            "description": "Some description",
            "duration": 120,
            "actors": [actor.id],
            "genres": [genres.id],
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
