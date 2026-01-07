import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")


def sample_movie(**params):
    defaults = {
        "title": "Sample movie",
        "description": "Sample description",
        "duration": 90,
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


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
            "test@test.com", "password123"
        )
        self.client.force_authenticate(self.user)

    def test_list_movies(self):
        sample_movie()
        res = self.client.get(MOVIE_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_title(self):
        movie1 = sample_movie(title="Avatar")
        sample_movie(title="Batman")
        res = self.client.get(MOVIE_URL, {"title": "Avatar"})

        serializer = MovieListSerializer(movie1)
        self.assertIn(serializer.data, res.data)

    def test_filter_movies_by_genres(self):
        genre = Genre.objects.create(name="Action")
        movie1 = sample_movie(title="Action Movie")
        movie1.genres.add(genre)
        sample_movie(title="Comedy Movie")

        res = self.client.get(MOVIE_URL, {"genres": f"{genre.id}"})
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], movie1.title)

    def test_filter_movies_by_actors(self):
        actor1 = Actor.objects.create(first_name="Leonardo", last_name="DiCaprio")
        actor2 = Actor.objects.create(first_name="Brad", last_name="Pitt")
        movie1 = sample_movie(title="Inception")
        movie2 = sample_movie(title="Once Upon a Time")
        movie1.actors.add(actor1)
        movie2.actors.add(actor2)

        res = self.client.get(MOVIE_URL, {"actors": f"{actor1.id},{actor2.id}"})
        self.assertEqual(len(res.data), 2)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        movie.genres.add(Genre.objects.create(name="Drama"))
        movie.actors.add(Actor.objects.create(first_name="Lulu", last_name="Rose"))

        url = detail_url(movie.id)
        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {"title": "T", "description": "D", "duration": 100}
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_image_upload_forbidden(self):
        movie = sample_movie()
        url = reverse("cinema:movie-upload-image", args=[movie.id])
        res = self.client.post(url, {"image": "test.jpg"}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = get_user_model().objects.create_superuser(
            "admin@test.com", "password123"
        )
        self.client.force_authenticate(self.admin)

    def test_create_movie(self):
        genre = Genre.objects.create(name="Drama")
        actor = Actor.objects.create(first_name="George", last_name="Clooney")

        payload = {
            "title": "New Movie",
            "description": "Description",
            "duration": 120,
            "genres": [genre.id],
            "actors": [actor.id],
        }
        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_upload_image_to_movie(self):
        movie = sample_movie()
        url = reverse("cinema:movie-upload-image", args=[movie.id])
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(url, {"image": ntf}, format="multipart")

        movie.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)
        self.assertTrue(os.path.exists(movie.image.path))
        movie.image.delete()
