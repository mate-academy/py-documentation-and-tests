import random
import string
import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor
from cinema.serializers import MovieDetailSerializer, MovieListSerializer

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
        "name": random.choices(string.ascii_letters, k=5),
    }
    defaults.update(params)

    return Genre.objects.create(**defaults)


def sample_actor(**params):
    defaults = {
        "first_name": random.choices(string.ascii_letters, k=5),
        "last_name": random.choices(string.ascii_letters, k=5),
    }
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


def image_upload_url(movie_id) -> str:
    """Return URL for recipe image upload"""
    return reverse("cinema:movie-upload-image", args=[movie_id])


def detail_url(movie_id) -> str:
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


class UnauthenticatedMovieApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_authentication_required(self) -> None:
        resp = self.client.get(MOVIE_URL)

        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        user = get_user_model().objects.create_user(
            email="user@movie.com", password="test_password"
        )
        self.client.force_authenticate(user)

    def test_movie_list(self) -> None:
        for _ in range(3):
            sample_movie()

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        resp = self.client.get(MOVIE_URL)

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data, serializer.data)

    def test_filter_movies_by_title(self) -> None:
        sample_movie(title="test")
        sample_movie(title="test_2")
        sample_movie(title="Oppenheimer")

        movies = Movie.objects.filter(title__icontains="test")
        serializer = MovieListSerializer(movies, many=True)

        resp = self.client.get(MOVIE_URL, {"title": "test"})

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data, serializer.data)

    def test_filter_movies_by_genres(self) -> None:
        for genre_id in range(3):
            sample_genre(name=f"genre_{genre_id}")

        sample_movie().genres.set([1, 2])
        sample_movie().genres.set([2])
        sample_movie().genres.set([3])

        movies = Movie.objects.filter(genres__id__in=[1, 2]).distinct()
        serializer = MovieListSerializer(movies, many=True)

        resp = self.client.get(MOVIE_URL, {"genres": "1,2"})

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data, serializer.data)

    def test_filter_movies_by_actors(self) -> None:
        for _ in range(3):
            sample_actor()

        sample_movie().actors.set([1, 2])
        sample_movie().actors.set([2])
        sample_movie().actors.set([3])

        movies = Movie.objects.filter(actors__id__in=[1, 2]).distinct()
        serializer = MovieListSerializer(movies, many=True)

        resp = self.client.get(MOVIE_URL, {"actors": "1,2"})

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data, serializer.data)

    def test_movie_detail(self) -> None:
        for genre_id in range(3):
            sample_genre(name=f"genre_{genre_id}")

        for _ in range(3):
            sample_actor()

        movie = sample_movie()
        movie.actors.set([1, 2, 3])
        movie.genres.set([1, 2, 3])
        serializer = MovieDetailSerializer(movie)

        resp = self.client.get(detail_url(movie.id))

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data, serializer.data)

    def test_movie_create_forbidden(self) -> None:
        payload = {
            "title": "Sample movie",
            "description": "Sample description",
            "duration": 90,
        }

        resp = self.client.post(MOVIE_URL, payload)

        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        user = get_user_model().objects.create_user(
            email="user@movie.com",
            password="test_password",
            is_staff=True,
        )
        self.client.force_authenticate(user)

    def test_movie_create(self) -> None:
        genre_1 = sample_genre(name="genre_1")
        genre_2 = sample_genre(name="genre_2")

        actor_1 = sample_actor()
        actor_2 = sample_actor()

        payload = {
            "title": "Sample movie",
            "description": "Sample description",
            "duration": 90,
            "genres": [genre_1.id, genre_2.id],
            "actors": [actor_1.id, actor_2.id],
        }

        resp = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=resp.data["id"])
        genres = movie.genres.all()
        actors = movie.actors.all()

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        del payload["genres"]
        del payload["actors"]

        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

        self.assertEqual(movie.genres.count(), 2)
        self.assertEqual(movie.actors.count(), 2)
        self.assertIn(genre_1, genres)
        self.assertIn(genre_2, genres)
        self.assertIn(actor_1, actors)
        self.assertIn(actor_2, actors)

    def test_movie_delete_not_allowed(self) -> None:
        movie = sample_movie()

        resp = self.client.delete(detail_url(movie.id))

        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
