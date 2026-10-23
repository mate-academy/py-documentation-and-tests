from unittest import TestCase

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer

MOVIE_URL = reverse("cinema:movie-list")


def sample_movie(**params) -> Movie:
    defaults = {
        "title": "Test_Drama",
        "description": "Drama",
        "duration": 50
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)


class UnauthenticatedMovieViewSetTests(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AauthenticatedMovieViewSetTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user, created = get_user_model().objects.get_or_create(
            email="auth_user@test.com"
        )
        if created:
            self.user.set_password("test123")
            self.user.save()
        self.client.force_authenticate(user=self.user)

    def test_movies_list(self):
        sample_movie()
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.data, serializer.data)

    def test_filter_movies(self):
        m1 = sample_movie(title="Drama")
        m2 = sample_movie(title="Action")

        g1 = Genre.objects.create(name="Drama")
        a1 = Actor.objects.create(first_name="Tom", last_name="Hardy")

        m1.genres.add(g1)
        m1.actors.add(a1)

        res_title = self.client.get(MOVIE_URL, {"title": "Drama"})
        self.assertEqual(len(res_title.data), 1)
        self.assertEqual(res_title.data[0]["title"], "Drama")

        res_genres = self.client.get(MOVIE_URL, {"genres": str(g1.id)})
        self.assertEqual(len(res_genres.data), 1)
        self.assertEqual(res_genres.data[0]["title"], "Drama")

        res_actors = self.client.get(MOVIE_URL, {"actors": str(a1.id)})
        self.assertEqual(len(res_actors.data), 1)
        self.assertEqual(res_actors.data[0]["title"], "Drama")
