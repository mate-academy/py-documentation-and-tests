import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor
from cinema.serializers import MovieSerializer, MovieListSerializer, MovieDetailSerializer

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
        res = self.client.post(url, {"image": "not image"}, format="multipart")

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


class UnauthenticatedMovieTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_movie_list(self):
        response = self.client.get(MOVIE_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "user@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)
        self.movie = sample_movie()
        self.genre = sample_genre()
        self.actor = sample_actor()

    def test_movie_list(self):
        sample_movie(title="Sample movie 2")
        movies = Movie.objects.all()
        response = self.client.get(MOVIE_URL)
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_filter_movies_by_title(self):
        movie = sample_movie(title="Sample movie 2")
        response = self.client.get(
            MOVIE_URL,
            data={"title": "Sample movie 2"}
        )
        serializer_correct_movie = MovieListSerializer(movie)
        serializer_incorrect_movie = MovieSerializer(self.movie)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(serializer_correct_movie.data, response.data)
        self.assertNotIn(serializer_incorrect_movie.data, response.data)

    def test_filter_movies_by_genre(self):
        movie = sample_movie(title="Sample movie 2")
        movie.genres.add(self.genre)
        response = self.client.get(
            MOVIE_URL,
            data={"genres": self.genre.id})
        serializer_correct_movie = MovieListSerializer(movie)
        serializer_incorrect_movie = MovieSerializer(self.movie)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(serializer_correct_movie.data, response.data)
        self.assertNotIn(serializer_incorrect_movie.data, response.data)

    def test_filter_movies_by_actor(self):
        movie = sample_movie(title="Sample movie 2")
        movie.actors.add(self.actor)
        response = self.client.get(
            MOVIE_URL,
            data={"actors": self.genre.id})
        serializer_correct_movie = MovieListSerializer(movie)
        serializer_incorrect_movie = MovieSerializer(self.movie)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(serializer_correct_movie.data, response.data)
        self.assertNotIn(serializer_incorrect_movie.data, response.data)

    def test_filter_movies_by_title_genre_actor(self):
        movie = sample_movie(title="Sample movie 2")
        movie.genres.add(self.genre)
        movie.actors.add(self.actor)
        response = self.client.get(
            MOVIE_URL,
            data={
                "title": "Sample movie 2",
                "genres": self.genre.id,
                "actors": self.actor.id,
            }
        )
        serializer_correct_movie = MovieListSerializer(movie)
        serializer_incorrect_movie = MovieSerializer(self.movie)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(serializer_correct_movie.data, response.data)
        self.assertNotIn(serializer_incorrect_movie.data, response.data)

    def test_movie_detail(self):
        response = self.client.get(detail_url(self.movie.id))
        serializer = MovieDetailSerializer(self.movie)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Sample movie 2",
            "description": "Sample description",
            "duration": 90,
        }
        response = self.client.post(MOVIE_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)
        self.movie = sample_movie()
        self.genre = sample_genre()
        self.actor = sample_actor()

    def test_create_movie(self):
        payload = {
            "title": "Sample movie 2",
            "description": "Sample description",
            "duration": 90
        }
        response = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=response.data["id"])

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_create_movie_with_genre_and_actor(self):
        payload = {
            "title": "Sample movie 2",
            "description": "Sample description",
            "duration": 90,
            "genres": self.genre.id,
            "actors": self.actor.id,
        }
        response = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=response.data["id"])

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn(self.genre, movie.genres.all())
        self.assertIn(self.actor, movie.actors.all())

    def test_delete_movie_not_allowed(self):
        response = self.client.delete(detail_url(self.movie.id))

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
