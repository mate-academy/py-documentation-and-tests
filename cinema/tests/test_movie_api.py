import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import (Movie,
                           Genre,
                           Actor,
                           CinemaHall,
                           MovieSession)

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


class PublicMovieAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_authentication_required_for_movie_list(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authentication_required_for_movie_detail(self):
        movie = sample_movie()
        res = self.client.get(detail_url(movie.id))
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Title",
            "description": "Description",
            "duration": 90,
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_upload_image_forbidden(self):
        movie = sample_movie()
        url = image_upload_url(movie.id)

        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(url, {"image": ntf}, format="multipart")
            self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AdminMovieAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = get_user_model().objects.create_superuser(
            "admin@test.com",
            "password",
        )
        self.client.force_authenticate(self.admin)

    def test_create_movie_success(self):
        genre = sample_genre()
        actor = sample_actor()
        payload = {
            "title": "New Movie",
            "description": "Description",
            "duration": 90,
            "genres": [genre.id],
            "actors": [actor.id]
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Movie.objects.filter(title="New Movie").exists())


class MovieSerializerTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_movie_list_serializer_structure(self):
        user = get_user_model().objects.create_user(
            email="user@test.com",
            password="password",
        )
        self.client.force_authenticate(user)
        genre = sample_genre(name="Genre")
        actor = sample_actor(first_name="Tommie", last_name="Hardy")
        movie = sample_movie(title="Movie")

        movie.genres.add(genre)
        movie.actors.add(actor)

        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertIsInstance(res.data[0]["genres"][0], str)
        self.assertIsInstance(res.data[0]["actors"][0], str)

    def test_movie_detail_serializer_structure(self):
        user = get_user_model().objects.create_user(
            email="user@test.com",
            password="password",
        )
        self.client.force_authenticate(user)

        genre = sample_genre(name="Drama")
        actor = sample_actor(first_name="Mike", last_name="Hardy")
        movie = sample_movie(title="Movie")

        movie.genres.add(genre)
        movie.actors.add(actor)

        res = self.client.get(detail_url(movie.id))

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertIsInstance(res.data["genres"][0], dict)
        self.assertIn("id", res.data["genres"][0])

        self.assertIsInstance(res.data["actors"][0], dict)
        self.assertIn("id", res.data["actors"][0])

    def test_filter_movie_by_title(self):
        user = get_user_model().objects.create_user(
            email="user@test.com",
            password="password",
        )
        self.client.force_authenticate(user)

        movie1 = sample_movie(title="Avatar")
        movie2 = sample_movie(title="Titanic")

        res = self.client.get(MOVIE_URL, {"title": "Ava"})

        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["id"], movie1.id)

    def test_filter_movie_by_genres(self):
        user = get_user_model().objects.create_user(
            email="user@test.com",
            password="password",
        )
        self.client.force_authenticate(user)

        genre1 = sample_genre(name="Drama")
        genre2 = sample_genre(name="Action")

        movie1 = sample_movie(title="Movie 1")
        movie2 = sample_movie(title="Movie 2")

        movie1.genres.add(genre1)
        movie2.genres.add(genre2)

        res = self.client.get(MOVIE_URL, {"genres": str(genre1.id)})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["id"], movie1.id)

    def test_filter_movie_by_actors(self):
        user = get_user_model().objects.create_user(
            email="user@test.com",
            password="password",
        )
        self.client.force_authenticate(user)

        actor1 = sample_actor(first_name="Tom", last_name="Hardy")
        actor2 = sample_actor(first_name="Mike", last_name="Hardy")

        movie1 = sample_movie(title="Movie 1")
        movie2 = sample_movie(title="Movie 2")

        movie1.actors.add(actor1)
        movie2.actors.add(actor2)
        res = self.client.get(MOVIE_URL, {"actors": str(actor1.id)})
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["id"], movie1.id)


class AuthenticatedMovieAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_authenticated_user_can_list_movies(self):
        user = get_user_model().objects.create_user(
            email="alex@gmail.com",
            password="password",
        )
        self.client.force_authenticate(user)
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_authenticated_user_can_retrieve_movie(self):
        user = get_user_model().objects.create_user(
            email="alex2@gmail.com",
            password="password2",
        )
        movie = sample_movie(title="Movie 2")
        self.client.force_authenticate(user)
        res = self.client.get(detail_url(movie.id))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_authenticated_user_cannot_create_movie(self):
        user = get_user_model().objects.create_user(
            email="alex3@gmail.com",
            password="password3",
        )
        self.client.force_authenticate(user)
        res = self.client.post(MOVIE_URL, {"title": "Movie 3"})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


    def test_authenticated_user_cannot_upload_image(self):
        user = get_user_model().objects.create_user(
            email="alex4@gmail.com",
            password="password4",
        )
        movie = sample_movie(title="Movie 4")
        self.client.force_authenticate(user)
        res = self.client.post(image_upload_url(movie.id))
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
