from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

CINEMA_URL = reverse("cinema:movie-list")


def detail_url(movie_id: int):
    return reverse("cinema:movie-detail", args=[movie_id])


class UnauthenticatedMovieApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(CINEMA_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


def sample_movie(**params):
    defaults = {
        "title": "Test Movie",
        "description": "description",
        "duration": 150,
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@test.com",
            "testuser",
        )
        self.client.force_authenticate(self.user)

    def test_list_movies(self):
        sample_movie()
        sample_movie()

        res = self.client.get(CINEMA_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_title(self):
        movie1 = sample_movie(title="Speed")
        movie2 = sample_movie(title="Slow")

        res = self.client.get(CINEMA_URL, {"title": "Speed"})

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)

        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

    def test_filter_movies_by_genres(self):
        movie1 = sample_movie(title="Meet with Focker")
        movie2 = sample_movie(title="Solt")

        genre1 = Genre.objects.create(name="Action")
        genre2 = Genre.objects.create(name="Horror")

        movie1.genres.add(genre1)
        movie2.genres.add(genre2)

        res = self.client.get(CINEMA_URL, {"genres": f"{genre1.id}"})

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)

        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

    def test_filter_movies_by_actors(self):
        movie1 = sample_movie(title="Speed")
        movie2 = sample_movie(title="Slow")

        actor1 = Actor.objects.create(first_name="Bob", last_name="Smith")
        actor2 = Actor.objects.create(first_name="Ewa", last_name="Mendez")

        movie1.actors.add(actor1)
        movie2.actors.add(actor2)

        res = self.client.get(CINEMA_URL, {"actors": f"{actor1.id}"})

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)

        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()

        url = detail_url(movie.id)
        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Test Movie",
            "description": "description",
            "duration": 150,
        }

        res = self.client.post(CINEMA_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApi(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@test.com",
            "testadmin",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)

    def test_delete_movie_not_allowed(self):
        movie = sample_movie()
        url = detail_url(movie.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
