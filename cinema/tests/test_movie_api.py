import tempfile
import os
from datetime import datetime
from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from cinema.models import (
    Movie,
    MovieSession,
    CinemaHall,
    Genre,
    Actor,
)
from cinema.serializers import (
    MovieListSerializer,
    MovieDetailSerializer,
)

MOVIE_URL = reverse("cinema:movie-list")
MOVIE_SESSION_URL = reverse("cinema:moviesession-list")


def sample_movie(**params) -> Movie:
    defaults = {
        "title": "Sample movie",
        "description": "Sample description",
        "duration": 90,
    }
    defaults.update(params)

    return Movie.objects.create(**defaults)


def sample_genre(**params) -> Genre:
    defaults = {
        "name": "Drama",
    }
    defaults.update(params)

    return Genre.objects.create(**defaults)


def sample_actor(**params) -> Actor:
    defaults = {"first_name": "George", "last_name": "Clooney"}
    defaults.update(params)

    return Actor.objects.create(**defaults)


def sample_movie_session(**params) -> MovieSession:
    cinema_hall = CinemaHall.objects.create(
        name="Blue", rows=20, seats_in_row=20
    )

    defaults = {
        "show_time": datetime(2022, 6, 2, 14, 0, 0),
        "movie": None,
        "cinema_hall": cinema_hall,
    }
    defaults.update(params)

    return MovieSession.objects.create(**defaults)


def image_upload_url(movie_id) -> object:
    """Return URL for recipe image upload"""
    return reverse("cinema:movie-upload-image", args=[movie_id])


def detail_url(movie_id) -> object:
    return reverse("cinema:movie-detail", args=[movie_id])


class MovieImageUploadTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)
        self.movie = sample_movie()
        self.genre = sample_genre()
        self.actor = sample_actor()
        self.movie_session = sample_movie_session(movie=self.movie)

    def tearDown(self) -> None:
        self.movie.image.delete()

    def test_upload_image_to_movie(self) -> None:
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

    def test_upload_image_bad_request(self) -> None:
        """Test uploading an invalid image"""
        url = image_upload_url(self.movie.id)
        res = self.client.post(url, {"image": "not image"}, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_image_to_movie_list(self) -> None:
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
                    "genres": [self.genre.id],
                    "actors": [self.actor.id],
                },
                format="multipart",
            )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(title="Title")
        self.assertFalse(bool(movie.image))

    def test_image_url_is_shown_on_movie_detail(self) -> None:
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(detail_url(self.movie.id))

        self.assertIn("image", res.data)

    def test_image_url_is_shown_on_movie_list(self) -> None:
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(MOVIE_URL)

        self.assertIn("image", res.data['results'][0].keys())

    def test_image_url_is_shown_on_movie_session_detail(self) -> None:
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(MOVIE_SESSION_URL)

        self.assertIn("movie_image", res.data['results'][0].keys())


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user.tests@gmail.com", password="TeSt1uSeR"
        )
        self.client.force_authenticate(self.user)
        self.genre = sample_genre(name="Action")
        self.actor = sample_actor(first_name="Tom", last_name="Cruise")

    def test_movies_list(self) -> None:
        sample_movie(title="Movie 1").genres.add(self.genre)
        sample_movie(title="Movie 2").actors.add(self.actor)

        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['results'], serializer.data)

    def test_filter_movies_by_title(self) -> None:
        movie1 = sample_movie(title="The Matrix")
        movie2 = sample_movie(title="Inception")

        res = self.client.get(MOVIE_URL, {"title": "Matrix"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data['results']), 1)
        self.assertEqual(res.data['results'][0]["title"], movie1.title)

    def test_filter_movies_by_genre(self) -> None:
        movie1 = sample_movie(title="Movie Action")
        movie1.genres.add(self.genre)
        movie2 = sample_movie(title="Movie Drama")

        res = self.client.get(MOVIE_URL, {"genres": self.genre.id})
        self.assertEqual(len(res.data['results']), 1)
        self.assertEqual(res.data['results'][0]["title"], movie1.title)

    def test_filter_movies_by_actor(self) -> None:
        movie1 = sample_movie(title="Mission Impossible")
        movie1.actors.add(self.actor)
        movie2 = sample_movie(title="Inception")

        res = self.client.get(MOVIE_URL, {"actors": self.actor.id})
        self.assertEqual(len(res.data['results']), 1)
        self.assertEqual(res.data['results'][0]["title"], movie1.title)

    def test_retrieve_movie_detail(self) -> None:
        movie = sample_movie(title="Interstellar")
        genre = sample_genre(name="Sci-Fi")
        actor = sample_actor(first_name="Matthew", last_name="McConaughey")
        movie.genres.add(genre)
        movie.actors.add(actor)

        url = detail_url(movie.id)
        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden_for_regular_user(self) -> None:
        payload = {
            "title": "Forbidden movie",
            "description": "Not allowed",
            "duration": 120,
            "genres": [self.genre.id],
            "actors": [self.actor.id],
        }
        res = self.client.post(MOVIE_URL, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.admin = get_user_model().objects.create_superuser(
            email="admin.tests@gmail.com", password="TeStAdMiNuSeR"
        )
        self.client.force_authenticate(self.admin)
        self.genre = sample_genre(name="Action")
        self.actor = sample_actor(first_name="Tom", last_name="Cruise")

    def test_create_movie(self) -> None:
        payload = {
            "title": "Admin Movie",
            "description": "Created by admin",
            "duration": 100,
            "genres": [self.genre.id],
            "actors": [self.actor.id],
        }

        res = self.client.post(MOVIE_URL, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        movie = Movie.objects.get(id=res.data["id"])
        self.assertEqual(movie.title, payload["title"])
