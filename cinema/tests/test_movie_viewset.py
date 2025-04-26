from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils.text import slugify
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from cinema.models import Movie, Actor, Genre
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

User = get_user_model()

MOVIES_LIST_URL = reverse("cinema:movie-list")


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


def sample_movie(**params):
    defaults = {
        "title": "Sample movie",
        "description": "Sample description",
        "duration": 90,
    }
    defaults.update(params)

    return Movie.objects.create(**defaults)


class UnauthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIES_LIST_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedBusApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="test@test.com",
            password="test12345"
        )
        self.client.force_authenticate(self.user)

    def test_movies_list(self):
        sample_movie()

        movie_with_actors = sample_movie()
        movie_with_genres = sample_movie()

        actor1 = Actor.objects.create(first_name="George", last_name="Clooney")
        actor2 = Actor.objects.create(first_name="John", last_name="Cleese")
        genre1 = Genre.objects.create(name="Drama")
        genre2 = Genre.objects.create(name="Action")

        movie_with_actors.actors.add(actor1, actor2)
        movie_with_genres.genres.add(genre1, genre2)

        res = self.client.get(MOVIES_LIST_URL)

        movies = Movie.objects.all()

        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_movies_list_with_filter_title(self):
        movie1 = sample_movie(title="test")
        movie2 = sample_movie(title="bred")

        res = self.client.get(MOVIES_LIST_URL, {"title": "test"})
        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)

        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

    def test_movies_list_with_filter_actors(self):
        movie1 = sample_movie()
        movie2 = sample_movie()

        actor1 = Actor.objects.create(first_name="George", last_name="Clooney")
        actor2 = Actor.objects.create(first_name="John", last_name="Cleese")

        movie1.actors.add(actor1)
        movie2.actors.add(actor2)

        res = self.client.get(MOVIES_LIST_URL, {"actors": actor1.id})

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)

        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

    def test_movies_list_with_filter_genres(self):
        movie1 = sample_movie()
        movie2 = sample_movie()

        genre1 = Genre.objects.create(name="Drama")
        genre2 = Genre.objects.create(name="Action")

        movie1.genres.add(genre1)
        movie2.genres.add(genre2)

        res = self.client.get(MOVIES_LIST_URL, {"genres": genre1.id})

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)

        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        movie.actors.add(Actor.objects.create(first_name="George", last_name="Clooney"))
        movie.genres.add(Genre.objects.create(name="Drama"))

        url = detail_url(movie.id)
        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "test movie",
            "description": "test description",
            "duration": 75,
        }

        res = self.client.post(MOVIES_LIST_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_upload_image_forbidden(self):
        movie = sample_movie()

        url = detail_url(movie.id) + "upload_image/"

        res = self.client.post(url, {"image": "test"}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email="test@test.com",
            password="test12345",
            is_staff=True,
        )
        self.client.force_authenticate(self.admin)

    def test_create_movie_successful(self):
        actor = Actor.objects.create(first_name="George", last_name="Clooney")
        genre = Genre.objects.create(name="Drama")
        payload = {
            "title": "test movie",
            "description": "test description",
            "duration": 75,
            "actors": [actor.id],
            "genres": [genre.id],
        }
        res = self.client.post(MOVIES_LIST_URL, payload)

        movie = Movie.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        for key in ["title", "description", "duration"]:
            self.assertEqual(payload[key], getattr(movie, key))

        self.assertEqual(
            sorted(payload["actors"]),
            sorted(list(movie.actors.values_list("id", flat=True))),
        )
        self.assertEqual(
            sorted(payload["genres"]),
            sorted(list(movie.genres.values_list("id", flat=True))),
        )

    def test_upload_image_successful(self):
        movie = sample_movie()

        image_data = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x01\x0A'
            b'\x00\x01\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        image = SimpleUploadedFile(
            "test.gif", image_data, content_type="image/gif"
        )

        image_url = detail_url(movie.id) + "upload_image/"
        res = self.client.post(image_url, {"image": image}, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        movie.refresh_from_db()
        self.assertIsNotNone(movie.image)
        self.assertIn(slugify(movie.title), movie.image.name)
        self.assertTrue(Path(movie.image.path).exists())

