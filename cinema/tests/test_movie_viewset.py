from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework.reverse import reverse
from django.contrib.auth import get_user_model

from cinema.models import Actor, Genre, Movie
from cinema.serializers import MovieListSerializer, MovieDetailSerializer


MOVIE_URL = reverse("cinema:movie-list")


def sample_movie(**params):
    actor = Actor.objects.create(
        first_name="Test_first_name", last_name="Test_last_name"
    )
    genre = Genre.objects.create(name="Test_name")
    default_movie = {
        "title": "Test",
        "description": "For test",
        "duration": 120,
    }
    default_movie.update(params)
    movie = Movie.objects.create(**default_movie)

    movie.actors.add(actor)
    movie.genres.add(genre)

    return movie


class UnauthenticatedMovieAPITests(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieAPITests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@tets.test", password="test_password"
        )
        self.client.force_authenticate(self.user)

    """Testing return all movies for auth. user"""

    def test_movie_list(self):
        sample_movie()

        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.data, serializer.data)

    """Testing post movie for auth. user"""

    def test_movie_post(self):
        payload = {
            "title": "Test",
            "description": "For test",
            "duration": 120,
        }
        actor = Actor.objects.create(
            first_name="Test_first_name", last_name="Test_last_name"
        )
        genre = Genre.objects.create(name="Test_name")

        payload["actors"] = [actor.id]
        payload["genres"] = [genre.id]

        res = self.client.post(MOVIE_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    """Testing show detail page movie for auth. user"""

    def test_movie_retrieve(self):
        movie = sample_movie()

        url = reverse("cinema:movie-detail", args=[movie.id])
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        movie_retrieve = Movie.objects.get(id=movie.id)
        serializer = MovieDetailSerializer(movie_retrieve)

        self.assertEqual(res.data, serializer.data)

    """Testing delete function for auth. user"""

    def test_movie_destroy(self):
        movie = sample_movie()

        url = reverse("cinema:movie-detail", args=[movie.id])
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
