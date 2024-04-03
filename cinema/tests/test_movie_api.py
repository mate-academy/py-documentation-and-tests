import tempfile

import os

import pytest

from model_bakery import baker

from PIL import Image

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")

MOVIE_SESSION_URL = reverse("cinema:moviesession-list")


def sample_movie(**params):
    defaults = {
        "title": "Sample movie",
        "description": "Sample description",
        "duration": 90,
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


def sample_movie_session(**params):
    cinema_hall = CinemaHall.objects.create(
        name="Blue", rows=20, seats_in_row=20
    )

    defaults = {
        "show_time": "2022-06-02 14:00:00",
        "movie": None,
        "cinema_hall": cinema_hall,
    }
    defaults.update(params)

    return MovieSession.objects.create(**defaults)


def image_upload_url(movie_id):
    """Return URL for recipe image upload"""
    return reverse("cinema:movie-upload-image", args=[movie_id])


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


class MovieImageUploadTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)
        self.movie = sample_movie()
        self.genre = sample_genre()
        self.actor = sample_actor()
        self.movie_session = sample_movie_session(movie=self.movie)

    def tearDown(self):
        self.movie.image.delete()

    def test_upload_image_to_movie(self):
        """Test uploading an image to movie"""
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(url, {"image": ntf}, format="multipart")
        self.movie.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)
        self.assertTrue(os.path.exists(self.movie.image.path))

    def test_upload_image_bad_request(self):
        """Test uploading an invalid image"""
        url = image_upload_url(self.movie.id)
        res = self.client.post(url, {"image": "not image"},
                               format="multipart")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_image_to_movie_list(self):
        url = MOVIE_URL
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(
                url,
                {
                    "title": "Title",
                    "description": "Description",
                    "duration": 90,
                    "genres": [1],
                    "actors": [1],
                    "image": ntf,
                },
                format="multipart",
            )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(title="Title")
        self.assertFalse(movie.image)

    def test_image_url_is_shown_on_movie_detail(self):
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(detail_url(self.movie.id))

        self.assertIn("image", res.data)

    def test_image_url_is_shown_on_movie_list(self):
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(MOVIE_URL)

        self.assertIn("image", res.data[0].keys())

    def test_image_url_is_shown_on_movie_session_detail(self):
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(MOVIE_SESSION_URL)

        self.assertIn("movie_image", res.data[0].keys())


class UnauthenticatedMovieAPITest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self):
        """
        Test for checking the authorization.

        return None

        expected HTTP-status: 401 (UNAUTHORIZED)
        """
        res_client = self.client.get(MOVIE_URL)
        self.assertEqual(
            res_client.status_code, status.HTTP_401_UNAUTHORIZED
        )


def movie_detail_url(movie_id):
    return reverse("cinema:movie-detail", args=(movie_id,))


class AuthenticatedMovieAPITest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="userauth.@test.com", password="userauth"
        )
        self.client.force_authenticate(self.user)

    def test_movies_list(self):
        """
        Test for getting the list of movie.

        return None

        expected HTTP-status: 200 (OK)
        """
        sample_movie()
        default_movie = sample_movie()

        t_actor = Actor.objects.create(first_name="Test", last_name="Actor")
        t_genre = Genre.objects.create(name="testgenre")

        default_movie.actors.set([t_actor])
        default_movie.genres.set([t_genre])

        res_client = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        movie_serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res_client.status_code, status.HTTP_200_OK)
        self.assertEqual(res_client.data, movie_serializer.data)

    def test_filtering_movies_by_genres(self):
        """
        Test for filtering the list by genres.

        return None
        """
        test_data = [
            {
                "movie": {"title": "Test Movie"},
                "genre": {"name": "testgenre"}
            },
            {
                "movie": {"title": "Movie Test"},
                "genre": {"name": "genretest"}
            },
            {
                "movie": {"title": "Test Movie: Test"},
                "genre": {"name": "testgenretest"}
            }
        ]

        test_movies = [
            sample_movie(**data["movie"]) for data in test_data
        ]

        test_genres = [
            Genre.objects.create(**data["genre"]) for data in test_data
        ]

        for movie, genre in zip(test_movies, test_genres):
            movie.genres.set([genre])

        genres_ids = ",".join(str(genre.id) for genre in test_genres)
        res_client = self.client.get(MOVIE_URL, {"genres": genres_ids})

        for movie in test_movies:
            movie_serializer = MovieListSerializer(movie)
            self.assertIn(movie_serializer.data, res_client.data)

    def test_filtering_movies_by_actors(self):
        """
        Test for filtering the list by actors.
        """
        test_data = [
            {
                "movie": {"title": "Test Movie"},
                "actor": {"first_name": "Test", "last_name": "Ac"}
            },
            {
                "movie": {"title": "Movie Test"},
                "actor": {"first_name": "Tes", "last_name": "tAc"}
            },
            {
                "movie": {"title": "Test Movie: Test"},
                "actor": {"first_name": "Act", "last_name": "Tes"}
            }
        ]

        test_movies = [
            sample_movie(**data["movie"]) for data in test_data
        ]

        test_actors = [
            Actor.objects.create(**data["actor"]) for data in test_data
        ]

        for movie, actor in zip(test_movies, test_actors):
            movie.actors.set([actor])

        actor_ids = ",".join(str(actor.id) for actor in test_actors)
        res_client = self.client.get(MOVIE_URL, {"actors": actor_ids})

        for movie in test_movies:
            movie_serializer = MovieListSerializer(movie)
            self.assertIn(movie_serializer.data, res_client.data)

    def test_movie_detail(self):
        """
        Test for getting the movie details.

        return None

        expected HTTP-status: 200 (OK)
        """
        test_genre = Genre.objects.create(name="testgenre")
        test_actor = Actor.objects.create(first_name="Test", last_name="Test")

        default_movie = sample_movie()
        default_movie.genres.set([test_genre])
        default_movie.actors.set([test_actor])

        url = movie_detail_url(default_movie.id)
        res_client = self.client.get(url)
        movie_serializer = MovieDetailSerializer(default_movie)

        self.assertEqual(res_client.status_code, status.HTTP_200_OK)
        self.assertEqual(res_client.data, movie_serializer.data)

    def test_movie_create_403_forbidden(self):
        """
        Test for creating the movie, creation should be not available.

        return None

        expected HTTP-status: 403 (FORBIDDEN)
        """
        test_genre_1 = Genre.objects.create(name="testgenre")
        test_actor_1 = Actor.objects.create(first_name="Test", last_name="Ac")

        test_movie = {
            "title": "Test",
            "description": "Movie for testing raising error 403",
            "duration": 403,
            "genres": [test_genre_1],
            "actors": [test_actor_1]
        }

        res_client = self.client.post(MOVIE_URL, test_movie)
        self.assertEqual(res_client.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

        self.user = get_user_model().objects.create_user(
            email="admin@test.com", password="Admin1###", is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_admin_create_movie_with_genres_and_actors(self):
        """
        Test for creating the movie, creation should be available.

        return None

        expected HTTP-status: 201 (CREATED)
        """
        test_genre_1 = Genre.objects.create(name="testgenre")
        test_genre_2 = Genre.objects.create(name="genretest")

        test_actor_1 = Actor.objects.create(first_name="Test", last_name="Ac")
        test_actor_2 = Actor.objects.create(first_name="Ac", last_name="Test")

        test_movie = {
            "title": "Test",
            "description": "Movie for testing admin permissions",
            "duration": 123,
            "genres": [test_genre_1.id, test_genre_2.id],
            "actors": [test_actor_1.id, test_actor_2.id]
        }
        res_client = self.client.post(MOVIE_URL, test_movie)

        self.assertEqual(res_client.status_code, status.HTTP_201_CREATED)

    def test_delete_movie_405_not_allowed(self):
        """
        Test for deleting the movie, but process should not be available.

        return None

        expected HTTP-status: 405 (METHOD_NOT_ALLOWED)
        """
        default_movie = sample_movie()
        url = movie_detail_url(default_movie.id)

        res_client = self.client.delete(url)

        self.assertEqual(
            res_client.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )
