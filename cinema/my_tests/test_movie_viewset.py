import os
import tempfile

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from PIL import Image

from cinema.models import Movie, Actor, Genre
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIES_URL = reverse("cinema:movie-list")


def detail_url(pk: int):
    return f"{reverse('cinema:movie-detail', args=[pk])}"


def sample_movie(**params):
    defaults = {"title": "test-title", "duration": 60, "description": "wow"}
    defaults.update(**params)
    return Movie.objects.create(**defaults)


def image_upload_url(movie_id):
    return reverse("cinema:movie-upload-image", args=[movie_id])


class MovieUnauthorizedTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_list_access_not_allowed(self):
        url = MOVIES_URL
        res = self.client.get(url)

        self.assertTrue(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_access_not_allowed(self):
        sample_movie()
        url = detail_url(1)
        res = self.client.get(url)

        self.assertTrue(res.status_code, status.HTTP_401_UNAUTHORIZED)


class MovieAuthorizedTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com", password="feoawv@!321"
        )
        self.client.force_authenticate(self.user)

    def test_list_movies(self):
        movie1 = sample_movie()
        movie2 = sample_movie(title="unique")

        url = MOVIES_URL
        res = self.client.get(url)
        serializer = MovieListSerializer([movie1, movie2], many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filtering_by_actors(self):
        Actor.objects.create(first_name="bob", last_name="alice")
        Actor.objects.create(first_name="william", last_name="the")
        movie_with_1actor = sample_movie()
        movie_with_2actors = sample_movie()
        movie_basic = sample_movie()

        movie_with_1actor.actors.add(1)
        movie_with_2actors.actors.add(1, 2)

        url = MOVIES_URL
        res = self.client.get(url, data={"actors": "1,2"})
        serializer_with_actors = MovieListSerializer(
            [movie_with_1actor, movie_with_2actors], many=True
        )
        serializer_without_actors = MovieListSerializer(movie_basic)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer_with_actors.data)
        self.assertNotIn(serializer_without_actors.data, res.data)

    def test_filtering_by_genres(self):
        Genre.objects.create(name="art")
        Genre.objects.create(name="love")
        movie_with_art = sample_movie()
        movie_with_lovart = sample_movie()
        movie_basic = sample_movie()

        movie_with_art.genres.add(1)
        movie_with_lovart.genres.add(1, 2)

        url = MOVIES_URL
        res = self.client.get(url, data={"genres": "1,2"})
        serializer_with_genres = MovieListSerializer(
            [movie_with_art, movie_with_lovart], many=True
        )
        serializer_without_genres = MovieListSerializer(movie_basic)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer_with_genres.data)
        self.assertNotIn(serializer_without_genres.data, res.data)

    def test_list_filtering_by_title(self):
        tit1 = sample_movie(title="titanic1")
        tit2 = sample_movie(title="titanic2")
        termite = sample_movie(title="termite")

        url = MOVIES_URL
        res = self.client.get(url, data={"title": "Titanic"})
        serializer_with_titanics = MovieListSerializer([tit1, tit2], many=True)
        serializer_without_titanics = MovieListSerializer(termite)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer_with_titanics.data)
        self.assertNotIn(serializer_without_titanics.data, res.data)

    def test_retrieve_movie_allowed(self):
        movie = sample_movie()

        url = detail_url(1)
        res = self.client.get(url)
        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_update_partial_update_movie_forbidden(self):
        Actor.objects.create(first_name="bob", last_name="alice")
        Genre.objects.create(name="ThomasMann")
        payload = {
            "title": "test-title",
            "duration": 60,
            "description": "wow",
            "actors": [1],
            "genres": [1],
        }
        url = MOVIES_URL
        res = self.client.post(url, data=payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        url = detail_url(1)
        payload["title"] = "updated"
        res = self.client.put(url, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        res = self.client.patch(url, data={"title": "patched"})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class MovieAdminTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.admin = get_user_model().objects.create_superuser(
            email="admin@test.com", password="esf@#!331"
        )
        self.client.force_authenticate(self.admin)

    def test_create_movie(self):
        actor = Actor.objects.create(first_name="bob", last_name="alice")
        genre = Genre.objects.create(name="ThomasMann")
        payload = {
            "title": "test-title",
            "duration": 60,
            "description": "wow",
            "actors": [1],
            "genres": [1],
        }
        url = MOVIES_URL
        res = self.client.post(url, data=payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.first()
        del payload["actors"]
        del payload["genres"]
        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))
        self.assertEqual(actor, movie.actors.first())
        self.assertEqual(genre, movie.genres.first())

    def test_delete_movie_forbidden(self):
        sample_movie()
        url = detail_url(1)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    class MovieImageUploadTests(TestCase):
        def setUp(self):
            self.client = APIClient()
            self.user = get_user_model().objects.create_superuser(
                "admin@myproject.com", "password"
            )
            self.client.force_authenticate(self.user)
            self.movie = sample_movie()
            self.genre = Genre.objects.create(name="art")
            self.actor = Actor.objects.create(
                first_name="bob", last_name="ali"
            )

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
            res = self.client.post(
                url, {"image": "not image"}, format="multipart"
            )

            self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        def test_post_image_to_movie_list(self):
            url = MOVIES_URL
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
