from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from cinema.serializers import (
    MovieListSerializer,
    MovieDetailSerializer,
    MovieSerializer,
)

MOVIE_URL = reverse("cinema:movie-list")


def sample_movie(**params):
    defaults = {
        "title": "Sample Movie",
        "description": "Some description",
        "duration": 50,
    }
    defaults.update(params)

    return Movie.objects.create(**defaults)


def sample_genre(**params):
    defaults = {
        "name": "Drama",
    }
    defaults.update(params)

    return Genre.objects.create(**defaults)


def sample_actor(**params):
    defaults = {"first_name": "George", "last_name": "Clooney"}
    defaults.update(params)

    return Actor.objects.create(**defaults)


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


class UnauthenticatedMovieApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user("user@user.com", "user")
        self.client.force_authenticate(self.user)

    def test_list_movies(self):
        sample_movie()
        sample_movie(title="movie with genre").genres.add(sample_genre())
        sample_movie(title="movie with actor").actors.add(sample_actor())

        response = self.client.get(MOVIE_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_movie_filters(self):
        movie_with_nothing = sample_movie(title="Movie with nothing")
        movie_with_actor = sample_movie(title="Movie with genre")
        movie_with_genre = sample_movie(title="Movie with actor")

        genre = sample_genre()
        actor = sample_actor()

        movie_with_actor.actors.add(actor)
        movie_with_genre.genres.add(genre)

        res1 = self.client.get(MOVIE_URL, {"title": "mov1ie"})
        res2 = self.client.get(MOVIE_URL, {"genres": f"{genre.id}"})
        res3 = self.client.get(MOVIE_URL, {"actors": f"{actor.id}"})

        serializer1 = MovieListSerializer(movie_with_nothing)
        serializer2 = MovieListSerializer(movie_with_genre)
        serializer3 = MovieListSerializer(movie_with_actor)

        self.assertNotIn(serializer1.data, res1.data)
        self.assertIn(serializer2.data, res2.data)
        self.assertIn(serializer3.data, res3.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()

        url = detail_url(movie.id)
        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Some secret movie",
            "description": "Some secret description",
            "duration": 50,
        }

        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@admin.com", "admin"
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        genre = sample_genre()
        actor = sample_actor()
        movie_info = {
            "title": "Some secret movie",
            "description": "Some secret description",
            "duration": 50,
            "actors": f"{actor.id}",
            "genres": f"{genre.id}",
        }

        res = self.client.post(MOVIE_URL, movie_info)
        movie = Movie.objects.get(id=res.data["id"])
        serializer = MovieSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(serializer.data, res.data)

    def test_delete_movie_not_allowed(self):
        movie = sample_movie()
        url = detail_url(movie.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_update_movie_not_allowed(self):
        movie = sample_movie()

        movie_put_data = {
            "title": "Put Movie",
            "description": "Put description",
            "duration": 51,
        }
        movie_patch_data = {
            "description": "Patch description",
        }

        res1 = self.client.put(detail_url(movie.id), movie_put_data)
        res2 = self.client.patch(detail_url(movie.id), movie_patch_data)

        self.assertEqual(res1.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(res2.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
