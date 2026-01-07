import tempfile

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile

from rest_framework import status
from rest_framework.test import APIClient

from PIL import Image

from cinema.models import Movie, Genre, Actor


MOVIE_LIST_URL = reverse("cinema:movie-list")


def movie_detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


def movie_upload_image_url(movie_id):
    return reverse("cinema:movie-upload-image", args=[movie_id])


def create_user(**params):
    return get_user_model().objects.create_user(**params)


def create_admin(**params):
    return get_user_model().objects.create_superuser(**params)


def create_movie(**params):
    defaults = {
        "title": "Test movie",
        "description": "Test description",
        "duration": 120,
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)


class MovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = create_user(
            email="user@test.com",
            password="pass1234",
        )
        self.admin = create_admin(
            email="admin@test.com",
            password="admin1234",
        )

    def test_list_movies_authenticated(self):
        self.client.force_authenticate(self.user)
        create_movie(title="Movie 1")
        create_movie(title="Movie 2")

        res = self.client.get(MOVIE_LIST_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)

    def test_list_movies_unauthenticated(self):
        create_movie()

        res = self.client.get(MOVIE_LIST_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_movie(self):
        self.client.force_authenticate(self.user)
        movie = create_movie(title="Detail movie")

        res = self.client.get(movie_detail_url(movie.id))

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["title"], movie.title)

    def test_create_movie_forbidden_for_user(self):
        self.client.force_authenticate(self.user)

        payload = {
            "title": "Forbidden",
            "description": "Nope",
            "duration": 100,
        }

        res = self.client.post(MOVIE_LIST_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_movie_allowed_for_admin(self):
        self.client.force_authenticate(self.admin)

        payload = {
            "title": "Admin movie",
            "description": "Allowed",
            "duration": 90,
        }

        res = self.client.post(MOVIE_LIST_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Movie.objects.filter(title="Admin movie").exists())


    def test_filter_movies_by_title(self):
        self.client.force_authenticate(self.user)
        create_movie(title="Batman")
        create_movie(title="Superman")

        res = self.client.get(MOVIE_LIST_URL, {"title": "bat"})

        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], "Batman")

    def test_filter_movies_by_genres(self):
        self.client.force_authenticate(self.user)
        genre1 = Genre.objects.create(name="Action")
        genre2 = Genre.objects.create(name="Drama")

        movie1 = create_movie(title="Movie 1")
        movie2 = create_movie(title="Movie 2")

        movie1.genres.add(genre1)
        movie2.genres.add(genre2)

        res = self.client.get(
            MOVIE_LIST_URL,
            {"genres": f"{genre1.id}"}
        )

        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], "Movie 1")

    def test_filter_movies_by_actors(self):
        self.client.force_authenticate(self.user)
        actor1 = Actor.objects.create(first_name="Tom", last_name="Hardy")
        actor2 = Actor.objects.create(first_name="Brad", last_name="Pitt")

        movie1 = create_movie(title="Movie 1")
        movie2 = create_movie(title="Movie 2")

        movie1.actors.add(actor1)
        movie2.actors.add(actor2)

        res = self.client.get(
            MOVIE_LIST_URL,
            {"actors": f"{actor1.id}"}
        )

        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], "Movie 1")

    def test_upload_image_to_movie_as_admin(self):
        self.client.force_authenticate(self.admin)
        movie = create_movie()

        with tempfile.NamedTemporaryFile(suffix=".jpg") as image:
            img = Image.new("RGB", (100, 100))
            img.save(image, format="JPEG")
            image.seek(0)

            payload = {"image": image}

            res = self.client.post(
                movie_upload_image_url(movie.id),
                payload,
                format="multipart",
            )

        movie.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(movie.image)

    def test_upload_image_forbidden_for_user(self):
        self.client.force_authenticate(self.user)
        movie = create_movie()

        payload = {
            "image": SimpleUploadedFile(
                "test.jpg",
                b"image-content",
                content_type="image/jpeg",
            )
        }

        res = self.client.post(
            movie_upload_image_url(movie.id),
            payload,
            format="multipart",
        )

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_movie_unauthenticated(self):
        movie = create_movie()

        res = self.client.get(movie_detail_url(movie.id))

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_upload_image_unauthenticated(self):
        movie = create_movie()

        with tempfile.NamedTemporaryFile(suffix=".jpg") as image:
            img = Image.new("RGB", (100, 100))
            img.save(image, format="JPEG")
            image.seek(0)

            payload = {"image": image}

            res = self.client.post(
                movie_upload_image_url(movie.id),
                payload,
                format="multipart",
            )

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
