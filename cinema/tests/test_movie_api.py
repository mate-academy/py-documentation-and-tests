import os
import tempfile

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import Actor, Genre, Movie


MOVIE_URL = reverse("cinema:movie-list")


def detail_url(movie_id: int) -> str:
    return reverse("cinema:movie-detail", args=[movie_id])


def image_upload_url(movie_id: int) -> str:
    return reverse("cinema:movie-upload-image", args=[movie_id])


def sample_genre(**params) -> Genre:
    defaults = {
        "name": "Drama",
    }
    defaults.update(params)
    return Genre.objects.create(**defaults)


def sample_actor(**params) -> Actor:
    defaults = {
        "first_name": "George",
        "last_name": "Clooney",
    }
    defaults.update(params)
    return Actor.objects.create(**defaults)


def sample_movie(**params) -> Movie:
    defaults = {
        "title": "Sample movie",
        "description": "Sample description",
        "duration": 90,
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)


class PublicMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user@example.com",
            password="testpass123",
        )
        self.client.force_authenticate(self.user)

    def test_list_movies(self):
        sample_movie(title="Movie 1")
        sample_movie(title="Movie 2")

        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)

    def test_retrieve_movie_detail(self):
        genre = sample_genre(name="Horror")
        actor = sample_actor(first_name="Keanu", last_name="Reeves")
        movie = sample_movie(title="Matrix")
        movie.genres.add(genre)
        movie.actors.add(actor)

        res = self.client.get(detail_url(movie.id))

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], movie.id)
        self.assertEqual(res.data["title"], movie.title)
        self.assertEqual(res.data["genres"][0]["name"], genre.name)
        self.assertEqual(
            res.data["actors"][0]["full_name"],
            f"{actor.first_name} {actor.last_name}",
        )

    def test_filter_movies_by_title(self):
        sample_movie(title="The Matrix")
        sample_movie(title="Toy Story")

        res = self.client.get(MOVIE_URL, {"title": "matrix"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], "The Matrix")

    def test_filter_movies_by_genres(self):
        genre1 = sample_genre(name="Action")
        genre2 = sample_genre(name="Comedy")

        movie1 = sample_movie(title="Movie 1")
        movie2 = sample_movie(title="Movie 2")

        movie1.genres.add(genre1)
        movie2.genres.add(genre2)

        res = self.client.get(MOVIE_URL, {"genres": str(genre1.id)})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["id"], movie1.id)

    def test_filter_movies_by_actors(self):
        actor1 = sample_actor(first_name="Actor", last_name="One")
        actor2 = sample_actor(first_name="Actor", last_name="Two")

        movie1 = sample_movie(title="Movie 1")
        movie2 = sample_movie(title="Movie 2")

        movie1.actors.add(actor1)
        movie2.actors.add(actor2)

        res = self.client.get(MOVIE_URL, {"actors": str(actor2.id)})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["id"], movie2.id)

    def test_create_movie_forbidden_for_non_admin(self):
        genre = sample_genre(name="Sci-Fi")
        actor = sample_actor(first_name="John", last_name="Doe")

        payload = {
            "title": "New movie",
            "description": "New description",
            "duration": 120,
            "genres": [genre.id],
            "actors": [actor.id],
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_user = get_user_model().objects.create_superuser(
            email="admin@example.com",
            password="testpass123",
        )
        self.client.force_authenticate(self.admin_user)

    def test_create_movie(self):
        genre1 = sample_genre(name="Sci-Fi")
        genre2 = sample_genre(name="Drama")
        actor1 = sample_actor(first_name="Actor", last_name="One")
        actor2 = sample_actor(first_name="Actor", last_name="Two")

        payload = {
            "title": "New movie",
            "description": "New description",
            "duration": 120,
            "genres": [genre1.id, genre2.id],
            "actors": [actor1.id, actor2.id],
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(id=res.data["id"])
        self.assertEqual(movie.title, payload["title"])
        self.assertEqual(movie.genres.count(), 2)
        self.assertEqual(movie.actors.count(), 2)


class MovieImageUploadTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            email="admin@myproject.com",
            password="password",
        )
        self.client.force_authenticate(self.user)
        self.movie = sample_movie()

    def tearDown(self):
        self.movie.image.delete()

    def test_upload_image_to_movie(self):
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
        url = image_upload_url(self.movie.id)
        res = self.client.post(url, {"image": "not image"}, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_image_to_movie_list_ignored(self):
        genre = sample_genre()
        actor = sample_actor()

        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(
                MOVIE_URL,
                {
                    "title": "Title",
                    "description": "Description",
                    "duration": 90,
                    "genres": [genre.id],
                    "actors": [actor.id],
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
