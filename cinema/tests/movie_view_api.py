from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework.reverse import reverse
from rest_framework import status

from cinema.models import Movie, Genre, Actor
from cinema.serializers import (
    MovieSerializer,
    MovieListSerializer,
    MovieDetailSerializer,
)

MOVIE_URL = reverse("cinema:movie-list")


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=(movie_id,))


def sample_movie(**params) -> Movie:
    defaults = {"title": "Duna", "duration": 180}
    defaults.update(params)
    movie = Movie.objects.create(**defaults)
    genre = Genre.objects.create(name="Action")
    actor = Actor.objects.create(first_name="Dave", last_name="Batista")

    movie.genres.add(genre)
    movie.actors.add(actor)
    return movie


class UnauthenticatedMovieApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.test", password="testpassword"
        )

        self.client.force_authenticate(self.user)

    def test_movies_list(self):
        sample_movie()

        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies(self):
        movie_1 = Movie.objects.create(duration=120)
        genre_action = Genre.objects.create(name="Action")
        actor_arnold = Actor.objects.create(
            first_name="Arnold", last_name="Schwarzenegger"
        )

        movie_1.genres.add(genre_action)
        movie_1.actors.add(actor_arnold)

        movie_2 = Movie.objects.create(duration=160)
        genre_fantastic = Genre.objects.create(name="Fantastic")
        actor_ben = Actor.objects.create(
            first_name="Ben", last_name="Affleck"
        )

        movie_2.genres.add(genre_action)
        movie_2.actors.add(actor_ben)

        res = self.client.get(
            MOVIE_URL,
            {
                "genre": f"{genre_action.id}, {genre_fantastic.id}",
                "actor": f"{actor_arnold.id}, {actor_ben.id}",
            },
        )

        serializer_movie_1 = MovieListSerializer(movie_1)
        serializer_movie_2 = MovieListSerializer(movie_2)

        self.assertIn(serializer_movie_1.data, res.data)
        self.assertIn(serializer_movie_2.data, res.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()

        url = detail_url(movie.id)
        res = self.client.get(url)
        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {"title": "Mechanic", "duration": 180}

        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@test.test",
            password="testpassword",
            is_staff=True,
        )

        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        payload = {"title": "Mechanic", "duration": 180}

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
