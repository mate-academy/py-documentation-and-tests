import tempfile
import os
from PIL import Image

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, Genre, Actor
from cinema.serializers import (
    MovieListSerializer,
    MovieDetailSerializer,
)


MOVIE_URL = reverse("cinema:movie-list")


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


def sample_genre(name="Action"):
    return Genre.objects.create(name=name)


def sample_actor(first_name="John", last_name="Doe"):
    return Actor.objects.create(first_name=first_name, last_name=last_name)


def sample_movie(**params):
    defaults = {
        "title": "Sample Movie",
        "description": "Sample description",
        "duration": 120,
    }
    defaults.update(params)

    movie = Movie.objects.create(**defaults)
    return movie


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
            password="testpass"
        )
        self.client.force_authenticate(self.user)

    def test_movie_list(self):
        movie = sample_movie()
        genre = sample_genre()
        actor = sample_actor()

        movie.genres.add(genre)
        movie.actors.add(actor)

        res = self.client.get(MOVIE_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"], serializer.data)

    def test_filter_by_title(self):
        m1 = sample_movie(title="Batman")
        m2 = sample_movie(title="Spiderman")

        res = self.client.get(MOVIE_URL, {"title": "bat"})

        serializer1 = MovieListSerializer(m1)
        serializer2 = MovieListSerializer(m2)

        self.assertIn(serializer1.data, res.data["results"])
        self.assertNotIn(serializer2.data, res.data["results"])

    def test_filter_by_genres(self):
        genre1 = sample_genre(name="Action")
        genre2 = sample_genre(name="Drama")

        movie1 = sample_movie(title="M1")
        movie2 = sample_movie(title="M2")
        movie3 = sample_movie(title="M3")

        movie1.genres.add(genre1)
        movie2.genres.add(genre2)

        res = self.client.get(
            MOVIE_URL,
            {"genres": f"{genre1.id},{genre2.id}"}
        )

        s1 = MovieListSerializer(movie1)
        s2 = MovieListSerializer(movie2)
        s3 = MovieListSerializer(movie3)

        self.assertIn(s1.data, res.data["results"])
        self.assertIn(s2.data, res.data["results"])
        self.assertNotIn(s3.data, res.data["results"])

    def test_filter_by_actors(self):
        actor1 = sample_actor(first_name="Tom")
        actor2 = sample_actor(first_name="Brad")

        movie1 = sample_movie(title="M1")
        movie2 = sample_movie(title="M2")
        movie3 = sample_movie(title="M3")

        movie1.actors.add(actor1)
        movie2.actors.add(actor2)

        res = self.client.get(
            MOVIE_URL,
            {"actors": f"{actor1.id},{actor2.id}"}
        )

        s1 = MovieListSerializer(movie1)
        s2 = MovieListSerializer(movie2)
        s3 = MovieListSerializer(movie3)

        self.assertIn(s1.data, res.data["results"])
        self.assertIn(s2.data, res.data["results"])
        self.assertNotIn(s3.data, res.data["results"])

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        movie.genres.add(sample_genre())
        movie.actors.add(sample_actor())

        url = detail_url(movie.id)
        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "New Movie",
            "description": "Desc",
            "duration": 100,
        }
        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)