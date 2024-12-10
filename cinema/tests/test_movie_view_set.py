from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")


def test_movie(**params) -> Movie:
    movie = {
        "title": "Test Movie",
        "description": "Test",
        "duration": 120,
    }
    movie.update(params)
    return Movie.objects.create(**movie)


def test_genre(**params) -> Genre:
    genre = {"name": "Drama"}
    genre.update(params)
    return Genre.objects.create(**genre)


def test_actor(**params) -> Actor:
    actor = {"first_name": "Tom", "last_name": "Hardy"}
    actor.update(params)
    return Actor.objects.create(**actor)


def movie_detail_url(movie_id: int):
    return reverse("cinema:movie-detail", args=(movie_id,))


class UnauthenticatedMovieViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required_movie_list(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_auth_required_movie_detail(self):
        movie = test_movie()
        url = movie_detail_url(movie.id)
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="sample@test.com",
            password="test_password"
        )
        self.client.force_authenticate(self.user)

    def test_movie_list(self):
        movie_with_genre = test_movie(title="Drama Movie")
        genre = test_genre()
        movie_with_genre.genres.add(genre)

        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_title(self):
        movie_1 = test_movie(title="Action Movie 1")

        res = self.client.get(MOVIE_URL, {"title": "Action Movie"})
        serializer = MovieListSerializer([movie_1], many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_genre(self):
        genre = test_genre(name="Action")
        movie_with_genre = test_movie(title="Action Movie")
        movie_with_genre.genres.add(genre)
        test_movie(title="Drama Movie")

        res = self.client.get(MOVIE_URL, {"genres": genre.id})
        serializer = MovieListSerializer([movie_with_genre], many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_retrieve_movie_detail(self):
        movie = test_movie()
        movie.genres.add(test_genre(name="Action"))
        movie.actors.add(test_actor())

        url = movie_detail_url(movie.id)
        res = self.client.get(url)
        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)


class AdminMovieTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@admin.com", password="password", is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        genre = test_genre()
        actor = test_actor()
        payload = {
            "title": "Some Movie",
            "description": "Regular movie.",
            "duration": 90,
            "genres": [genre.id],
            "actors": [actor.id],
        }
        res = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(movie.title, payload["title"])
        self.assertEqual(movie.description, payload["description"])
        self.assertEqual(movie.duration, payload["duration"])
        self.assertEqual(list(movie.genres.all()), [genre])
        self.assertEqual(list(movie.actors.all()), [actor])
