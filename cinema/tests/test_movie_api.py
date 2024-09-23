import os
import tempfile

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.admin import User
from rest_framework.test import APIClient, APITestCase

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")
MOVIE_SESSION_URL = reverse("cinema:moviesession-list")


def sample_movie(**params):
    defaults = {
        "title": "Sample movie",
        "description": "Sample description",
        "duration": 90,
    }
    defaults.update(params)

    return Movie.objects.create(**defaults)


def sample_genre(**params):
    defaults = {
        "name": "Drama",
    }
    defaults.update(params)

    return Genre.objects.create(**defaults)


def sample_actor(**params):
    defaults = {"first_name": "George", "last_name": "Clooney"}
    defaults.update(params)

    return Actor.objects.create(**defaults)


def sample_movie_session(**params):
    cinema_hall = CinemaHall.objects.create(
        name="Blue", rows=20, seats_in_row=20
    )

    defaults = {
        "show_time": "2022-06-02 14:00:00",
        "movie": None,
        "cinema_hall": cinema_hall,
    }
    defaults.update(params)

    return MovieSession.objects.create(**defaults)


def image_upload_url(movie_id):
    """Return URL for recipe image upload"""
    return reverse("cinema:movie-upload-image", args=[movie_id])


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


class MovieImageUploadTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)
        self.movie = sample_movie()
        self.genre = sample_genre()
        self.actor = sample_actor()
        self.movie_session = sample_movie_session(movie=self.movie)

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
        res = self.client.post(url, {"image": "not image"}, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_image_to_movie_list(self):
        url = MOVIE_URL
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

    def test_image_url_is_shown_on_movie_session_detail(self):
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(MOVIE_SESSION_URL)

        self.assertIn("movie_image", res.data[0].keys())


class UnAuthenticatedMovieApiTest(APITestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(MOVIE_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com",
            password="testpass"
        )
        self.client.force_authenticate(self.user)

    def test_movie_list(self):
        sample_movie()
        movie_with_actors_genres = sample_movie()

        actor = sample_actor()
        genre = sample_genre()

        movie_with_actors_genres.actors.add(actor)
        movie_with_actors_genres.genres.add(genre)

        response = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(response.data, serializer.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_movies_filter_genres(self):
        movie_without_genre = sample_movie()
        movie_with_genre_1 = sample_movie()
        movie_with_genre_2 = sample_movie()

        genre_1 = sample_genre(name="test_genre_1")
        genre_2 = sample_genre(name="test_genre_2")

        movie_with_genre_1.genres.add(genre_1)
        movie_with_genre_2.genres.add(genre_2)

        response = self.client.get(
            MOVIE_URL,
            {
                "genres": f"{genre_1.id},{genre_2.id}"
            }
        )

        serializer_without_genre = MovieListSerializer(movie_without_genre)
        serializer_with_genre_1 = MovieListSerializer(movie_with_genre_1)
        serializer_with_genre_2 = MovieListSerializer(movie_with_genre_2)

        self.assertIn(serializer_with_genre_1.data, response.data)
        self.assertIn(serializer_with_genre_2.data, response.data)
        self.assertNotIn(serializer_without_genre.data, response.data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_movies_filter_actors(self):
        movie_without_actor = sample_movie()
        movie_with_actor_1 = sample_movie()
        movie_with_actor_2 = sample_movie()

        actor_1 = sample_actor(first_name="Alice", last_name="Smith")
        actor_2 = sample_actor(first_name="Adam", last_name="Black")

        movie_with_actor_1.actors.add(actor_1)
        movie_with_actor_2.actors.add(actor_2)

        response = self.client.get(
            MOVIE_URL,
            {"actors": f"{actor_1.id},{actor_2.id}"}
        )

        serializer_without_actor = MovieListSerializer(movie_without_actor)
        serializer_with_actor_1 = MovieListSerializer(movie_with_actor_1)
        serializer_with_actor_2 = MovieListSerializer(movie_with_actor_2)

        self.assertIn(serializer_with_actor_1.data, response.data)
        self.assertIn(serializer_with_actor_2.data, response.data)
        self.assertNotIn(serializer_without_actor.data, response.data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_movie_title(self):
        movie_title = sample_movie()
        movie_title_1 = sample_movie(title="Test")

        response = self.client.get(
            MOVIE_URL,
            {"title": "Test"}
        )

        serializer_with_title = MovieListSerializer(movie_title)
        serializer_with_with_title_1 = MovieListSerializer(movie_title_1)

        self.assertIn(serializer_with_with_title_1.data, response.data)
        self.assertNotIn(serializer_with_title.data, response.data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_movies_retrieve(self):
        movie = sample_movie()

        url = detail_url(movie.id)

        response = self.client.get(url)
        serializer = MovieDetailSerializer(movie)
        self.assertEqual(response.data, serializer.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "title",
            "description": "description",
            "duration": 132,
        }
        response = self.client.post(MOVIE_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_superuser(
            email="admin@admin.com",
            password="admin@123",
            is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        payload = {
            "title": "title",
            "description": "description",
            "duration": 132,
        }
        response = self.client.post(MOVIE_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_movie_with_actor(self):
        actor = sample_actor()

        payload = {
            "title": "title",
            "description": "description",
            "duration": 132,
            "actor": [actor.id]
        }

        response = self.client.post(MOVIE_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_movie_with_genre(self):
        genre = sample_genre()

        payload = {
            "title": "title",
            "description": "description",
            "duration": 132,
            "genre": [genre.id]
        }

        response = self.client.post(MOVIE_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_delete_movie(self):
        movie = sample_movie()

        response = self.client.delete(detail_url(movie.id))

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
