import tempfile
import os
from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer


MOVIE_URL = reverse("cinema:movie-list")


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])

def sample_movie(**params):
    defaults = {
        "title": "Test movie",
        "description": "Test description",
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
            email="user@test.com",
            password="pass123",
        )
        self.client.force_authenticate(self.user)

    def test_movies_list(self):
        sample_movie()
        sample_movie(title="Another movie")

        res = self.client.get(MOVIE_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        for movie in movies:
            self.assertIn(MovieListSerializer(movie).data, res.data)

    def test_filter_movies_by_genres(self):
        genre_1 = Genre.objects.create(name="Action")
        genre_2 = Genre.objects.create(name="Drama")

        movie_1 = sample_movie(title="Movie 1")
        movie_2 = sample_movie(title="Movie 2")
        movie_3 = sample_movie(title="Movie 3")

        movie_1.genres.add(genre_1)
        movie_2.genres.add(genre_2)

        res = self.client.get(
            MOVIE_URL,
            {"genres": f"{genre_1.id},{genre_2.id}"}
        )

        self.assertIn(MovieListSerializer(movie_1).data, res.data)
        self.assertIn(MovieListSerializer(movie_2).data, res.data)
        self.assertNotIn(MovieListSerializer(movie_3).data, res.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()

        res = self.client.get(detail_url(movie.id))
        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {"title": "Forbidden", "description": "desc"}

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_filter_movies_by_title(self):
        movie_1 = sample_movie(title="Matrix")
        movie_2 = sample_movie(title="Avatar")

        res = self.client.get(MOVIE_URL, {"title": "Matrix"})

        self.assertIn(MovieListSerializer(movie_1).data, res.data)
        self.assertNotIn(MovieListSerializer(movie_2).data, res.data)

    def test_filter_movies_by_actors(self):
        actor_1 = Actor.objects.create(first_name="Tom", last_name="Hardy")
        actor_2 = Actor.objects.create(first_name="Brad", last_name="Pitt")

        movie_1 = sample_movie(title="Movie 1")
        movie_2 = sample_movie(title="Movie 2")

        movie_1.actors.add(actor_1)
        movie_2.actors.add(actor_2)

        res = self.client.get(MOVIE_URL, {"actors": actor_1.id})

        self.assertIn(MovieListSerializer(movie_1).data, res.data)
        self.assertNotIn(MovieListSerializer(movie_2).data, res.data)

def image_upload_url(movie_id):
    return reverse("cinema:movie-upload-image", args=[movie_id])


class AdminMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = get_user_model().objects.create_superuser(
            email="admin@test.com",
            password="pass123",
        )
        self.client.force_authenticate(self.admin)

    def test_create_movie(self):
        genre = Genre.objects.create(name="Action")
        actor = Actor.objects.create(first_name="Tom", last_name="Hardy")

        payload = {
            "title": "Admin movie",
            "description": "desc",
            "duration": 120,
            "genres": [genre.id],
            "actors": [actor.id],
        }

        res = self.client.post(MOVIE_URL, payload)


        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Movie.objects.filter(title=payload["title"]).exists()
        )

    def test_upload_image_to_movie(self):
        movie = sample_movie()

        url = image_upload_url(movie.id)

        with tempfile.NamedTemporaryFile(suffix=".jpg") as image_file:
            img = Image.new("RGB", (100, 100))
            img.save(image_file, format="JPEG")
            image_file.seek(0)

            res = self.client.post(
                url,
                {"image": image_file},
                format="multipart",
            )

        movie.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(movie.image)
        self.assertTrue(os.path.exists(movie.image.path))
