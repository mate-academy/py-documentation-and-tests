from rest_framework.test import APITestCase, APIClient
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from django.contrib.auth import get_user_model
from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor
from cinema.serializers import MovieListSerializer

MOVIE_VIEW_SET_URL = reverse("cinema:movie-list")


def sample_movie(**params) -> Movie:
    defaults = {
        "title": "Sample Movie",
        "description": "Some sample description.",
        "duration": 120,
    }
    defaults.update(params)
    movie = Movie.objects.create(**defaults)
    return movie


class UnauthenticatedMovieViewSetApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_VIEW_SET_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieViewSetApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@test.com", password="adminpass"
        )
        self.client.force_authenticate(self.user)


    def test_movies_list(self):
        sample_movie()
        res = self.client.get(MOVIE_VIEW_SET_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_title(self):
        sample_movie(title="The Matrix")
        sample_movie(title="Inception")

        res = self.client.get(MOVIE_VIEW_SET_URL, {"title": "matrix"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], "The Matrix")

    def test_filter_movies_by_genres(self):
        genre1 = Genre.objects.create(name="Sci-Fi")
        genre2 = Genre.objects.create(name="Action")

        movie1 = sample_movie(title="Interstellar")
        movie2 = sample_movie(title="John Wick")

        movie1.genres.add(genre1)
        movie2.genres.add(genre2)

        res = self.client.get(MOVIE_VIEW_SET_URL, {"genres": f"{genre1.id}"})

        serializer1 = MovieListSerializer(movie1)
        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(MovieListSerializer(movie2).data, res.data)

    def test_filter_movies_by_actors(self):
        actor1 = Actor.objects.create(first_name="Keanu", last_name="Reeves")
        actor2 = Actor.objects.create(first_name="Leonardo", last_name="DiCaprio")

        movie1 = sample_movie(title="Matrix")
        movie2 = sample_movie(title="Titanic")

        movie1.actors.add(actor1)
        movie2.actors.add(actor2)

        res = self.client.get(MOVIE_VIEW_SET_URL, {"actors": f"{actor1.id}"})

        self.assertIn(MovieListSerializer(movie1).data, res.data)
        self.assertNotIn(MovieListSerializer(movie2).data, res.data)
