from io import BytesIO
from unittest.mock import patch

from PIL import Image
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from cinema.models import Movie, Actor, Genre
from cinema.serializers import (
    MovieListSerializer,
    MovieDetailSerializer,
    MovieImageSerializer,
    MovieSerializer,
)
from cinema.views import MovieViewSet

MOVIE_URL = reverse("cinema:movie-list")


def sample_movie(**params) -> Movie:
    defaults = {
        "title": "MovieTitle",
        "description": "MovieDescription",
        "duration": 12345,
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)


class UnauthenticatedMovieViewSetTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("cinema.views.MovieViewSet.permission_classes", [AllowAny])
    def test_throttling_anonymous(self):
        cache.clear()
        for num in range(11):
            res = self.client.get(MOVIE_URL)
            if num < 10:
                self.assertNotEqual(res.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
            else:
                self.assertEqual(res.status_code, status.HTTP_429_TOO_MANY_REQUESTS)


class GetTokensTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()

    def test_tokens(self):
        get_user_model().objects.create_user(
            email="test@example.com", password="testpass123"
        )
        response = self.client.post(
            "/api/user/token/", {"email": "test@example.com", "password": "testpass123"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

        refresh_token = response.data["refresh"]

        refresh_res = self.client.post(
            "/api/user/token/refresh/", {"refresh": refresh_token}
        )

        self.assertEqual(refresh_res.status_code, 200)
        self.assertIn("access", refresh_res.data)


class AuthenticatedMovieViewSetTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test_user@example.com",
            password="testuser",
        )
        response = self.client.post(
            "/api/user/token/",
            {"email": "test_user@example.com", "password": "testuser"},
        )

        self.token = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

    def test_list_movies_missing_token(self):
        self.client.credentials()  # Remove token
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_movies_invalid_token(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer invalidtoken123")
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_movies_list(self):
        sample_movie()

        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_by_title_movies(self):
        movie_one = sample_movie(title="Inception")
        movie_two = sample_movie(title="Interstellar")

        res = self.client.get(MOVIE_URL, {"title": f"{movie_one.title}"})

        serializer_one = MovieListSerializer(movie_one)
        serializer_two = MovieListSerializer(movie_two)

        self.assertIn(serializer_one.data, res.data)
        self.assertNotIn(serializer_two.data, res.data)

        res = self.client.get(MOVIE_URL, {"title": "in"})
        self.assertIn(serializer_one.data, res.data)
        self.assertIn(serializer_two.data, res.data)

    def test_filter_by_actor_movies(self):
        movie_one = sample_movie(title="Inception")
        movie_two = sample_movie(title="Interstellar")

        actor_one = Actor.objects.create(first_name="Leonardo", last_name="DiCaprio")
        actor_two = Actor.objects.create(first_name="Matthew", last_name="McConaughey")

        movie_one.actors.add(actor_one)
        movie_two.actors.add(actor_two)

        res = self.client.get(MOVIE_URL, {"actors": f"{actor_one.id}"})

        serializer_one = MovieListSerializer(movie_one)
        serializer_two = MovieListSerializer(movie_two)

        self.assertIn(serializer_one.data, res.data)
        self.assertNotIn(serializer_two.data, res.data)

    def test_filter_by_genre_movies(self):
        movie_one = sample_movie(title="Inception")
        movie_two = sample_movie(title="Interstellar")

        genre_one = Genre.objects.create(name="action")
        genre_two = Genre.objects.create(name="science-fiction")

        movie_one.genres.add(genre_one)
        movie_two.genres.add(genre_two)

        res = self.client.get(MOVIE_URL, {"genres": f"{genre_one.id}"})

        serializer_one = MovieListSerializer(movie_one)
        serializer_two = MovieListSerializer(movie_two)

        self.assertIn(serializer_one.data, res.data)
        self.assertNotIn(serializer_two.data, res.data)

    def test_movie_detail(self):
        sample_movie()
        movie_one = sample_movie(title="Inception")

        res = self.client.get(
            reverse("cinema:movie-detail", kwargs={"pk": movie_one.id})
        )
        movie = Movie.objects.get(id=movie_one.id)
        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_not_admin_forbidden(self):
        payload = {
            "title": "Inception",
            "description": "MovieDescription",
            "duration": 12345,
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_put_movie_not_admin_forbidden(self):
        movie = sample_movie()
        movie = Movie.objects.get(id=movie.id)
        payload = {
            "title": "NewMovieTitle",
            "description": "NewMovieDescription",
            "duration": 12345,
        }
        movie_to_put_url = reverse("cinema:movie-detail", kwargs={"pk": movie.id})
        res = self.client.put(movie_to_put_url, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_patch_movie_not_admin_forbidden(self):
        movie = sample_movie()
        movie = Movie.objects.get(id=movie.id)
        payload = {
            "duration": 12345,
        }
        movie_to_patch_url = reverse("cinema:movie-detail", kwargs={"pk": movie.id})
        res = self.client.patch(movie_to_patch_url, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_movie_image_not_admin_forbidden(self):
        movie = sample_movie()
        url = reverse("cinema:movie-upload-image", kwargs={"pk": movie.id})
        image = SimpleUploadedFile(
            name="test.jpg", content=b"fake-image-content", content_type="image/jpeg"
        )

        res = self.client.post(url, {"image": image}, format="multipart")
        movie.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_throttling_user(self):
        cache.clear()
        for num in range(31):
            res = self.client.get(MOVIE_URL)
            if num < 30:
                self.assertEqual(res.status_code, status.HTTP_200_OK)
            else:
                self.assertEqual(res.status_code, status.HTTP_429_TOO_MANY_REQUESTS)


class AdminMovieViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test_admin@example.com",
            password="testadmin",
            is_staff=True,
        )
        response = self.client.post(
            "/api/user/token/",
            {"email": "test_admin@example.com", "password": "testadmin"},
        )
        self.token = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

    def test_create_movie_admin(self):
        genre = Genre.objects.create(name="action")
        actor = Actor.objects.create(first_name="Matthew", last_name="McConaughey")
        payload = {
            "title": "Inception",
            "description": "MovieDescription",
            "duration": 12345,
            "actors": [actor.id],
            "genres": [genre.id],
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(title="Inception")
        self.assertEqual(movie.description, "MovieDescription")
        self.assertEqual(movie.duration, 12345)

    def test_put_movie_admin(self):
        movie = sample_movie()
        movie = Movie.objects.get(id=movie.id)
        payload = {
            "title": "NewMovieTitle",
            "description": "NewMovieDescription",
            "duration": 12345,
        }
        movie_to_put_url = reverse("cinema:movie-detail", kwargs={"pk": movie.id})
        res = self.client.put(movie_to_put_url, payload)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_patch_movie_admin(self):
        movie = sample_movie()
        movie = Movie.objects.get(id=movie.id)
        payload = {
            "duration": 12345,
        }
        movie_to_patch_url = reverse("cinema:movie-detail", kwargs={"pk": movie.id})
        res = self.client.patch(movie_to_patch_url, payload)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_movie_admin_forbidden(self):
        movie_one = sample_movie(title="Inception")
        serializer = MovieListSerializer(movie_one)

        res = self.client.get(MOVIE_URL)
        self.assertIn(serializer.data, res.data)

        movie_to_delete_url = reverse(
            "cinema:movie-detail", kwargs={"pk": movie_one.id}
        )
        res = self.client.delete(movie_to_delete_url)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_admin_add_movie_image(self):
        movie = sample_movie()
        url = reverse("cinema:movie-upload-image", kwargs={"pk": movie.id})

        image_io = BytesIO()
        image = Image.new("RGB", (100, 100), color="red")
        image.save(image_io, format="JPEG")
        image_io.seek(0)

        uploaded_image = SimpleUploadedFile(
            name="test.jpg", content=image_io.read(), content_type="image/jpeg"
        )

        res = self.client.post(url, {"image": uploaded_image}, format="multipart")
        movie.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)
        self.assertTrue(movie.image.name.endswith(".jpg"))


class MovieViewSetSerializerClassTest(TestCase):
    def setUp(self):
        self.viewset = MovieViewSet()

    def test_list_action_uses_list_serializer(self):
        self.viewset.action = "list"
        serializer_class = self.viewset.get_serializer_class()
        self.assertEqual(serializer_class, MovieListSerializer)

    def test_retrieve_action_uses_detail_serializer(self):
        self.viewset.action = "retrieve"
        serializer_class = self.viewset.get_serializer_class()
        self.assertEqual(serializer_class, MovieDetailSerializer)

    def test_upload_image_action_uses_image_serializer(self):
        self.viewset.action = "upload_image"
        serializer_class = self.viewset.get_serializer_class()
        self.assertEqual(serializer_class, MovieImageSerializer)

    def test_default_action_uses_base_serializer(self):
        self.viewset.action = "create"
        serializer_class = self.viewset.get_serializer_class()
        self.assertEqual(serializer_class, MovieSerializer)
