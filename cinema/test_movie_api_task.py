from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


def sample_movie(**params):
    defaults = {
        "title": "Test Movie",
        "description": "Test Description",
        "duration": 120,
    }
    defaults.update(params)

    return Movie.objects.create(**defaults)


class UnauthenticatedMovieApiTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

        self.user = get_user_model().objects.create_user(
            email="test@gmail.com",
            password="password123",
        )

        self.client.force_authenticate(self.user)

    def test_movie_list(self):
        sample_movie(title="Test Movie 1")
        sample_movie(title="Test Movie 2")

        res = self.client.get(MOVIE_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_movie_retrieve(self):
        movie = sample_movie(title="Test Retrieve Movie")

        res = self.client.get(detail_url(movie.id))

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_title(self):
        movie = sample_movie(title="Test Movie Title")
        sample_movie(title="Another Movie")

        res = self.client.get(MOVIE_URL, {"title": "Test"})

        serializer = MovieListSerializer([movie], many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_genre(self):
        genre1 = Genre.objects.create(name="Test Genre 1")
        genre2 = Genre.objects.create(name="Test Genre 2")

        movie1 = sample_movie(title="Test Movie 1")
        movie2 = sample_movie(title="Test Movie 2")
        movie3 = sample_movie(title="Test Movie 3")

        movie1.genres.add(genre1)
        movie2.genres.add(genre2)
        movie3.genres.add(genre1, genre2)

        res = self.client.get(
            MOVIE_URL,
            {"genres": f"{genre1.id},{genre2.id}"}
        )

        expected = Movie.objects.filter(
            genres__id__in=[genre1.id, genre2.id]
        ).distinct()

        serializer = MovieListSerializer(expected, many=True)

        self.assertCountEqual(res.data, serializer.data)

    def test_filter_movies_by_actor(self):
        actor1 = Actor.objects.create(
            first_name="Test",
            last_name="Actor1",
        )
        actor2 = Actor.objects.create(
            first_name="Test",
            last_name="Actor2",
        )

        movie1 = sample_movie(title="Test Movie 1")
        movie2 = sample_movie(title="Test Movie 2")
        movie3 = sample_movie(title="Test Movie 3")

        movie1.actors.add(actor1)
        movie2.actors.add(actor2)
        movie3.actors.add(actor1, actor2)

        res = self.client.get(
            MOVIE_URL,
            {"actors": f"{actor1.id},{actor2.id}"}
        )

        expected = Movie.objects.filter(
            actors__id__in=[actor1.id, actor2.id]
        ).distinct()

        serializer = MovieListSerializer(expected, many=True)

        self.assertCountEqual(res.data, serializer.data)
