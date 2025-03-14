import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor
from cinema.serializers import (
    MovieListSerializer,
    MovieDetailSerializer,
)

MOVIE_URL = reverse("cinema:movie-list")
MOVIE_SESSION_URL = reverse("cinema:moviesession-list")

def detail_movie_url(movie_id: int) -> str:
    return reverse("cinema:movie-detail", args=(movie_id,))

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


class UnauthenticatedApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="testuser@myproject.com",
            password="password"
        )
        self.client.force_authenticate(self.user)

    def test_get_all_movies_list(self):
        sample_movie()
        test_movie = sample_movie()
        test_genre = sample_genre()

        test_movie.genres.add(test_genre)

        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_genre(self):
        movie_without_genre = sample_movie()
        movie_with_genre = sample_movie()
        movie_with_another_genre = sample_movie()
        genre = sample_genre()
        another_genre = sample_genre(name="Comedy")
        movie_with_genre.genres.add(genre)
        movie_with_another_genre.genres.add(another_genre)

        res = self.client.get(MOVIE_URL, {"genres": genre.id})

        serializer_movie_without_genre = MovieListSerializer(movie_without_genre)
        serializer_movie_with_genre = MovieListSerializer(movie_with_genre)
        serializer_movie_another_genre = MovieListSerializer(movie_with_another_genre)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer_movie_with_genre.data, res.data)
        self.assertNotIn(serializer_movie_without_genre.data, res.data)
        self.assertNotIn(serializer_movie_another_genre.data, res.data)

    def test_filter_movies_by_title(self):
        movie1 = sample_movie(title="Test title")
        movie2 = sample_movie(title="Test title 2")
        movie3 = sample_movie(title="Title")

        res = self.client.get(MOVIE_URL, {"title": "Test"})

        serializer_movie1 = MovieListSerializer(movie1)
        serializer_movie2 = MovieListSerializer(movie2)
        serializer_movie3 = MovieListSerializer(movie3)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer_movie1.data, res.data)
        self.assertIn(serializer_movie2.data, res.data)
        self.assertNotIn(serializer_movie3.data, res.data)
        self.assertEqual(len(res.data), 2)

    def test_filter_movies_by_actors(self):
        movie_with_actor_solo = sample_movie()
        movie_with_actor_many = sample_movie()
        movie_without_actor = sample_movie()
        actor = sample_actor()
        target_actor = sample_actor(first_name="Test", last_name="Actor")
        movie_with_actor_solo.actors.add(target_actor)
        movie_with_actor_many.actors.add(target_actor, actor)
        movie_without_actor.actors.add(actor)

        res = self.client.get(MOVIE_URL, {"actors": target_actor.id})

        serializer_movie_w_actor_solo = MovieListSerializer(movie_with_actor_solo)
        serializer_movie_w_actor_many = MovieListSerializer(movie_with_actor_many)
        serializer_movie_w_no_actor = MovieListSerializer(movie_without_actor)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer_movie_w_actor_solo.data, res.data)
        self.assertIn(serializer_movie_w_actor_many.data, res.data)
        self.assertNotIn(serializer_movie_w_no_actor.data, res.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()

        url = detail_movie_url(movie.id)
        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Test Movie",
            "description": "Sample description",
            "duration": 90,
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="testadmin@myproject.com",
            password="password",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)

    def test_create_movie_with_admin_permission(self):
        payload = {
            "title": "Test Movie",
            "description": "Sample description",
            "duration": 90
        }

        res = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

        self.assertEqual(Movie.objects.count(), 1)


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
