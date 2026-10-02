from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework.reverse import reverse
from rest_framework import status
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
import io

from cinema.models import Movie, Genre, Actor
from cinema.serializers import (
    MovieListSerializer,
    MovieDetailSerializer
)

MOVIE_LIST_URL = reverse("cinema:movie-list")

def create_sample_movie(**params) -> Movie:
    defaults = {
        "title": "Default",
        "description": "Default",
        "duration": 60,
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)

def detail_url(movie_id):
    return reverse(
        "cinema:movie-detail",
        args=[movie_id]
    )


class UnauthenticatedMovieViewSetTests(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(MOVIE_LIST_URL)
        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED
        )


class AuthenticatedMovieViewSetTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.test",
            password="test1password"
        )
        self.client.force_authenticate(user=self.user)

    def test_movie_list(self):
        create_sample_movie()
        response = self.client.get(MOVIE_LIST_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )
        self.assertEqual(
            response.data,
            serializer.data
        )

    def test_movie_title_filter(self):
        default_movie = create_sample_movie()
        filtered_movie = create_sample_movie(title="Test")

        response = self.client.get(
            MOVIE_LIST_URL,
            {"title": filtered_movie.title}
        )

        serializer_no_filter = MovieListSerializer(default_movie)
        serializer_filtered = MovieListSerializer(filtered_movie)

        self.assertIn(
            serializer_filtered.data,
            response.data
        )
        self.assertNotIn(
            serializer_no_filter.data,
            response.data
        )

    def test_movie_genres_filter(self):
        default_movie = create_sample_movie()
        filtered_movie = create_sample_movie()

        genre = Genre.objects.create(name="Test")

        filtered_movie.genres.add(genre)

        response = self.client.get(
            MOVIE_LIST_URL,
            {"genres": genre.id}
        )

        serializer_default = MovieListSerializer(default_movie)
        serializer_filtered = MovieListSerializer(filtered_movie)

        self.assertIn(
            serializer_filtered.data,
            response.data
        )
        self.assertNotIn(
            serializer_default.data,
            response.data
        )

    def test_movie_actor_filter(self):
        default_movie = create_sample_movie()
        filtered_movie = create_sample_movie()

        actor = Actor.objects.create(
            first_name="Test",
            last_name="Test",
        )

        filtered_movie.actors.add(actor)

        response = self.client.get(
            MOVIE_LIST_URL,
            {"actors": actor.id}
        )

        serializer_default = MovieListSerializer(default_movie)
        serializer_filtered = MovieListSerializer(filtered_movie)

        self.assertIn(
            serializer_filtered.data,
            response.data
        )
        self.assertNotIn(
            serializer_default.data,
            response.data
        )

    def test_movie_retrieve(self):
        movie = create_sample_movie()
        movie.genres.add(Genre.objects.create(name="Test"))

        url = detail_url(movie.id)

        response = self.client.get(url)

        serializer= MovieDetailSerializer(movie)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )
        self.assertEqual(
            response.data,
            serializer.data
        )

    def test_post_forbidden(self):
        payload_movie_info = {
            "title": "Test",
            "description": "Test",
            "duration": 60,
        }
        image = SimpleUploadedFile(
            "test_image.jpg",
            b"test_image",
            content_type="image/jpeg"
        )

        response_info = self.client.post(
            MOVIE_LIST_URL,
            payload_movie_info
        )
        response_image = self.client.post(
            MOVIE_LIST_URL,
            {"image": image},
            format="multipart"
        )

        self.assertEqual(
            response_info.status_code,
            status.HTTP_403_FORBIDDEN
        )
        self.assertEqual(
            response_image.status_code,
            status.HTTP_403_FORBIDDEN
        )


class AdminMovieViewSetTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@admin.test",
            password="admin1password",
            is_staff = True
        )
        self.client.force_authenticate(user=self.user)

    def test_post_movie(self):
        payload_movie_info = {
            "title": "Test",
            "description": "Test",
            "duration": 60,
        }

        response = self.client.post(
            MOVIE_LIST_URL,
            payload_movie_info
        )

        movie = Movie.objects.get(id=response.data["id"])

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )

        for key in payload_movie_info:
            self.assertEqual(
                payload_movie_info[key], getattr(movie, key)
            )

    def test_post_movie_genres_and_actors(self):
        genre = Genre.objects.create(name="Test")

        actor = Actor.objects.create(
            first_name="Test",
            last_name="Test",
        )

        payload = {
            "title": "Test",
            "description": "Test",
            "duration": 60,
            "genres": [genre.id],
            "actors": [actor.id],
        }

        response = self.client.post(
            MOVIE_LIST_URL,
            payload
        )

        movie = Movie.objects.get(id=response.data["id"])
        genres = movie.genres.all()
        actors = movie.actors.all()

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )
        self.assertIn(
            genre,
            genres
        )
        self.assertEqual(
            genres.count(),
            1
        )
        self.assertIn(
            actor,
            actors
        )
        self.assertEqual(
            actors.count(),
            1
        )

    def test_post_movie_image(self):
        movie = create_sample_movie()

        image = Image.new(
            "RGB",
            (100, 100),
            color="red"
        )
        buffer = io.BytesIO()
        image.save(buffer, "JPEG")
        buffer.seek(0)
        uploaded_image = SimpleUploadedFile(
            "test_image.jpg",
            buffer.read(),
            content_type="image/jpeg"
        )
        url = reverse(
            "cinema:movie-upload-image",
            args=[movie.id]
        )
        response = self.client.post(
            url,
            {"image": uploaded_image},
            format="multipart"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

