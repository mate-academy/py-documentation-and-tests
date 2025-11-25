from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework.reverse import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from cinema.models import Movie
from cinema.serializers import MovieListSerializer, MovieDetailSerializer
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cinema_service.settings")
django.setup()

MOVIE_URL = reverse("cinema:movie-list")


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=(movie_id,))


def upload_image_url(movie_id):
    return reverse("cinema:movie-upload-image", args=[movie_id])


def sample_movie(**params) -> Movie:
    defaults = {
        "title": "Sample Movie",
        "description": "Some description",
        "duration": 120,
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)


class UnauthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.test", password="testpass1"
        )
        self.client.force_authenticate(self.user)

    def test_list_movies(self):
        sample_movie()
        sample_movie(title="Another Movie")

        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"], serializer.data)

    def test_filter_movies_by_title(self):
        movie1 = sample_movie(title="Avengers")
        sample_movie(title="Batman")

        res = self.client.get(MOVIE_URL, {"title": "Avengers"})
        serializer = MovieListSerializer(movie1)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer.data, res.data["results"])

    def test_filter_movies_by_genres(self):
        movie1 = sample_movie(title="Action Movie")
        movie2 = sample_movie(title="Comedy Movie")

        genre_action = movie1.genres.create(name="Action")
        genre_comedy = movie2.genres.create(name="Comedy")

        res = self.client.get(MOVIE_URL, {"genres": f"{genre_action.id},{genre_comedy.id}"})
        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)

        self.assertIn(serializer1.data, res.data["results"])
        self.assertIn(serializer2.data, res.data["results"])

    def test_filter_movies_by_actors(self):
        movie1 = sample_movie(title="Hero Movie")
        movie2 = sample_movie(title="Villain Movie")

        actor1 = movie1.actors.create(name="Actor 1")
        actor2 = movie2.actors.create(name="Actor 2")

        res = self.client.get(MOVIE_URL, {"actors": f"{actor1.id}"})
        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)

        self.assertIn(serializer1.data, res.data["results"])
        self.assertNotIn(serializer2.data, res.data["results"])

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        url = detail_url(movie.id)

        res = self.client.get(url)
        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {"title": "New Movie", "description": "Desc", "duration": 100}
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_upload_image(self):
        movie = sample_movie()
        url = upload_image_url(movie.id)

        image = SimpleUploadedFile(
            "test_image.jpg", b"file_content", content_type="image/jpeg"
        )
        res = self.client.post(url, {"image": image}, format="multipart")
        movie.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(bool(movie.image))


class AdminMovieTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@admin.test", password="adminpass", is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        payload = {"title": "New Movie", "description": "Desc", "duration": 110}
        res = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(id=res.data["id"])
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_update_movie(self):
        movie = sample_movie()
        payload = {"title": "Updated Title"}
        url = detail_url(movie.id)

        res = self.client.patch(url, payload)
        movie.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(movie.title, payload["title"])

    def test_delete_movie(self):
        movie = sample_movie()
        url = detail_url(movie.id)

        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Movie.objects.filter(id=movie.id).exists())

    def test_upload_image(self):
        movie = sample_movie()
        url = upload_image_url(movie.id)

        image = SimpleUploadedFile(
            "test_image.jpg", b"file_content", content_type="image/jpeg"
        )
        res = self.client.post(url, {"image": image}, format="multipart")
        movie.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(bool(movie.image))
