from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer
from cinema.tests.test_movie_api import (
    sample_movie,
    sample_actor,
    sample_genre,
    detail_url,
    MOVIE_URL)


class UnauthenticatedMovieViewSetTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self) -> None:
        response = self.client.get(MOVIE_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieViewSetTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@user.com",
            password="testpassword"
        )
        self.client.force_authenticate(self.user)

        self.movie = sample_movie()

        self.actor = sample_actor(first_name="Ryan", last_name="Gosling")
        self.genre = sample_genre(name="Drama")
        self.movie_with_filter = sample_movie(title="Barbie")
        self.movie_with_filter.actors.add(self.actor)
        self.movie_with_filter.genres.add(self.genre)

    def test_all_movies_list(self):
        response = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(response.data, serializer.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_filter_movies_by_title(self):
        response = self.client.get(MOVIE_URL, {"title": "movie"})
        serializer_movie_wf = MovieListSerializer(self.movie_with_filter)
        serializer_movie = MovieListSerializer(self.movie)

        self.assertNotIn(serializer_movie_wf.data, response.data)
        self.assertIn(serializer_movie.data, response.data)

    def test_filter_movies_by_genre(self):
        response = self.client.get(MOVIE_URL, {"genres": 1})
        serializer_movie_wf = MovieListSerializer(self.movie_with_filter)
        serializer_movie = MovieListSerializer(self.movie)

        self.assertNotIn(serializer_movie.data, response.data)
        self.assertIn(serializer_movie_wf.data, response.data)

    def test_filter_movies_by_actor(self):
        response = self.client.get(MOVIE_URL, {"actors": 1})
        serializer_movie_wf = MovieListSerializer(self.movie_with_filter)
        serializer_movie = MovieListSerializer(self.movie)

        self.assertNotIn(serializer_movie.data, response.data)
        self.assertIn(serializer_movie_wf.data, response.data)

    def test_retrieve_movie(self):
        url = detail_url(self.movie.id)
        response = self.client.get(url)
        serializer = MovieDetailSerializer(self.movie)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "wwz",
            "description": "World War Z",
            "duration": "120"
        }
        response = self.client.post(MOVIE_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieViewSetTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@admin.com",
            password="testpassword",
            is_staff=True
        )

        self.client.force_authenticate(self.user)

        self.actor = sample_actor(first_name="Ryan", last_name="Gosling")
        self.genre = sample_genre(name="Drama")
        self.movie_with_filter = sample_movie(title="Barbie")
        self.movie_with_filter.actors.add(self.actor.pk)
        self.movie_with_filter.genres.add(self.genre.pk)

    def test_create_movie_admin(self):
        payload = {
            "title": "wwz",
            "description": "World War Z",
            "duration": "120"
        }

        response = self.client.post(MOVIE_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        actors = Actor.objects.all()
        genres = Genre.objects.all()

        self.assertIn(self.actor, actors)
        self.assertEqual(actors.count(), 1)

        self.assertIn(self.genre, genres)
        self.assertEqual(genres.count(), 1)

    def test_delete_movie_is_not_allowed(self):
        url = detail_url(self.movie_with_filter.pk)
        response = self.client.delete(url)

        self.assertEqual(response.status_code,
                         status.HTTP_405_METHOD_NOT_ALLOWED)
