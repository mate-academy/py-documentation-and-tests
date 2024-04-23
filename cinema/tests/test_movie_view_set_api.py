from io import BytesIO

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.core.files.uploadedfile import SimpleUploadedFile

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieDetailSerializer, MovieListSerializer

MOVIE_URL = reverse("cinema:movie-list")


def detailed_url(movie_id) -> str:
    return reverse("cinema:movie-detail", args=[movie_id])


def sample_movie(**params) -> Movie:
    defaults = {
        "title": "Sample movie",
        "description": "Sample description",
        "duration": 120,
    }
    defaults.update(params)

    return Movie.objects.create(**defaults)


def temporary_image():
    bts = BytesIO()
    img = Image.new("RGB", (100, 100))
    img.save(bts, 'jpeg')
    return SimpleUploadedFile("test.jpg", bts.getvalue())


class UnauthenticatedTestMovieViewSetApiTest(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_authentication_required(self):
        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedTestMovieViewSetApiTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com", password="testpass123"
        )
        self.client.force_authenticate(self.user)

    def test_movies_list(self):
        sample_movie()
        movie_with_genres = sample_movie()
        genre1 = Genre.objects.create(name="Action")
        genre2 = Genre.objects.create(name="Comedy")
        movie_with_genres.genres.add(genre1, genre2)

        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_movies_list_with_filters(self):
        movie_without_genre = sample_movie()
        movie_with_genre1 = sample_movie(title="Movie with genre 1")
        movie_with_genre2 = sample_movie(title="Movie with genre 2")

        genre_1 = Genre.objects.create(name="Genre 1")
        genre_2 = Genre.objects.create(name="Genre 2")
        movie_with_genre1.genres.add(genre_1)
        movie_with_genre2.genres.add(genre_2)

        res = self.client.get(
            MOVIE_URL, {"genres": f"{genre_1.id}, {genre_2.id}"}
        )

        serializer_without_genre = MovieListSerializer(movie_without_genre)
        serializer_with_genre1 = MovieListSerializer(movie_with_genre1)
        serializer_with_genre2 = MovieListSerializer(movie_with_genre2)

        self.assertIn(serializer_with_genre1.data, res.data)
        self.assertIn(serializer_with_genre2.data, res.data)
        self.assertNotIn(serializer_without_genre.data, res.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        genre = Genre.objects.create(name="Action")
        actor = Actor.objects.create(first_name="John", last_name="Doe")
        movie.genres.add(genre)
        movie.actors.add(actor)

        url = detailed_url(movie.id)
        res = self.client.get(url)
        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Sample movie",
            "description": "Sample description",
            "duration": 120,
        }
        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_movie_forbidden(self):
        movie = sample_movie()
        payload = {"title": "New title"}

        url = detailed_url(movie.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminTestMovieViewSetApiTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin_user = get_user_model().objects.create_user(
            email="test-admin@gmail.com",
            password="password123",
            is_staff=True,
        )
        self.client.force_authenticate(self.admin_user)

        self.genre = Genre.objects.create(name="Action")
        self.actor = Actor.objects.create(first_name="John", last_name="Doe")

    def test_create_movie(self):

        payload = {
            "title": "Sample movie",
            "description": "Sample description",
            "duration": 120,
            "genres": [self.genre.id],
            "actors": [self.actor.id],
        }

        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        movie = Movie.objects.get(id=res.data["id"])
        for key, value in payload.items():
            if key == "genres" or key == "actors":
                continue
            self.assertEqual(value, getattr(movie, key))

        self.assertEqual(movie.genres.first().name, self.genre.name)
        self.assertEqual(movie.actors.first().full_name, self.actor.full_name)

    def test_create_movie_with_image(self):

        movie_payload = {
            "title": "Sample movie with image",
            "description": "Sample description",
            "duration": 120,
            "genres": [self.genre.id],
            "actors": [self.actor.id],
        }
        movie_res = self.client.post(MOVIE_URL, movie_payload)
        movie_id = movie_res.data["id"]

        upload_url = f"/api/cinema/movies/{movie_id}/upload-image/"
        image = temporary_image()
        upload_res = self.client.post(
            upload_url, {"image": image}, format="multipart"
        )
        self.assertEqual(upload_res.status_code, status.HTTP_200_OK)
        movie = Movie.objects.get(id=movie_id)
        self.assertTrue(movie.image)
