import os
import tempfile

from PIL import Image

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor


MOVIE_URL = reverse("cinema:movie-list")


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


def image_upload_url(movie_id):
    return reverse("cinema:movie-upload-image", args=[movie_id])


def sample_genre(name="Drama"):
    return Genre.objects.create(name=name)


def sample_actor(
    first_name="Tom",
    last_name="Hanks",
):
    return Actor.objects.create(
        first_name=first_name,
        last_name=last_name,
    )


def sample_movie(**params):
    defaults = {
        "title": "Sample movie",
        "description": "Sample description",
        "duration": 120,
    }

    defaults.update(params)

    return Movie.objects.create(**defaults)


class UnauthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)

        self.assertEqual(
            res.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="user@test.com",
            password="testpass123",
        )

        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_list_movies(self):
        sample_movie(title="Movie 1")
        sample_movie(title="Movie 2")

        res = self.client.get(MOVIE_URL)

        self.assertEqual(
            res.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(len(res.data), 2)

    def test_retrieve_movie(self):
        movie = sample_movie()

        res = self.client.get(detail_url(movie.id))

        self.assertEqual(
            res.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            res.data["title"],
            movie.title,
        )

    def test_filter_movies_by_title(self):
        movie1 = sample_movie(title="Avatar")
        sample_movie(title="Batman")

        res = self.client.get(
            MOVIE_URL,
            {"title": "Avatar"},
        )

        self.assertEqual(len(res.data), 1)

        self.assertEqual(
            res.data[0]["id"],
            movie1.id,
        )

    def test_filter_movies_by_genres(self):
        genre1 = sample_genre(name="Drama")
        genre2 = sample_genre(name="Comedy")

        movie1 = sample_movie(title="Movie 1")
        movie2 = sample_movie(title="Movie 2")

        movie1.genres.add(genre1)
        movie2.genres.add(genre2)

        res = self.client.get(
            MOVIE_URL,
            {"genres": str(genre1.id)},
        )

        self.assertEqual(len(res.data), 1)

        self.assertEqual(
            res.data[0]["id"],
            movie1.id,
        )

    def test_filter_movies_by_actors(self):
        actor1 = sample_actor(
            first_name="Tom",
            last_name="Hanks",
        )

        actor2 = sample_actor(
            first_name="Brad",
            last_name="Pitt",
        )

        movie1 = sample_movie(title="Movie 1")
        movie2 = sample_movie(title="Movie 2")

        movie1.actors.add(actor1)
        movie2.actors.add(actor2)

        res = self.client.get(
            MOVIE_URL,
            {"actors": str(actor1.id)},
        )

        self.assertEqual(len(res.data), 1)

        self.assertEqual(
            res.data[0]["id"],
            movie1.id,
        )


class AdminMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.admin = get_user_model().objects.create_superuser(
            email="admin@test.com",
            password="admin123",
        )

        self.client.force_authenticate(self.admin)

    def tearDown(self):
        Movie.objects.all().delete()

    def test_create_movie(self):
        genre = sample_genre()
        actor = sample_actor()

        payload = {
            "title": "Interstellar",
            "description": "Space movie",
            "duration": 169,
            "genres": [genre.id],
            "actors": [actor.id],
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(
            res.status_code,
            status.HTTP_201_CREATED,
        )

        movie = Movie.objects.get(id=res.data["id"])

        self.assertEqual(
            movie.title,
            payload["title"],
        )

    def test_upload_image_to_movie(self):
        movie = sample_movie()

        url = image_upload_url(movie.id)

        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)

            res = self.client.post(
                url,
                {"image": ntf},
                format="multipart",
            )

        movie.refresh_from_db()

        self.assertEqual(
            res.status_code,
            status.HTTP_200_OK,
        )

        self.assertTrue(bool(movie.image))

    def test_upload_image_bad_request(self):
        movie = sample_movie()

        url = image_upload_url(movie.id)

        res = self.client.post(
            url,
            {"image": "not image"},
            format="multipart",
        )

        self.assertEqual(
            res.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
