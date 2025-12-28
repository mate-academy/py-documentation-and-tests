import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import (
    Movie,
    MovieSession,
    CinemaHall,
    Genre,
    Actor
)
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


class UnauthorizedUserMovieTests(TestCase):
    def test_unauthorized_user_access(self):
        self.client = APIClient()
        response = self.client.get(MOVIE_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthorizedUserMovieTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)

    def test_get_movies_list(self):
        sample_movie()
        sample_movie()
        sample_movie()
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)
        response = self.client.get(MOVIE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_get_movies_with_title_filter(self):
        sample_movie()
        sample_movie()
        movie = Movie.objects.create(
            title="Test movie",
            description="Test description",
            duration=93,
        )
        serializer = MovieListSerializer([movie], many=True)
        response = self.client.get(
            MOVIE_URL,
            data={"title": "test"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(serializer.data, response.data)

    def test_get_movies_with_actors_filter(self):
        sample_movie()
        sample_movie()
        movie = Movie.objects.create(
            title="Test movie",
            description="Test description",
            duration=93,
        )
        actor_1 = sample_actor()
        actor_2 = sample_actor(last_name="Black")
        movie.actors.add(actor_1, actor_2)
        serializer = MovieListSerializer([movie], many=True)
        response = self.client.get(
            MOVIE_URL,
            data={"actors": f"{actor_1.id},{actor_2.id}"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(serializer.data, response.data)

    def test_get_movies_with_genre_filter(self):
        sample_movie()
        sample_movie()
        movie = Movie.objects.create(
            title="Test movie",
            description="Test description",
            duration=93,
        )
        genre_1 = sample_genre()
        genre_2 = sample_genre(name="Horror")
        movie.genres.add(genre_1, genre_2)
        serializer = MovieListSerializer([movie], many=True)
        response = self.client.get(
            MOVIE_URL,
            data={"genres": f"{genre_1.id},{genre_2.id}"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(serializer.data, response.data)

    def test_get_movie_detail(self):
        movie = sample_movie()
        serializer = MovieDetailSerializer(movie)
        url = detail_url(movie.id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_user_access_post_request(self):
        response = self.client.post(
            MOVIE_URL,
            data={
                "title": "Test movie",
                "description": "Test description",
                "duration": 93,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminUserMovieTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        payload = {
            "title": "Test movie",
            "description": "Test description",
            "duration": 93,
        }
        response = self.client.post(
            MOVIE_URL,
            data=payload
        )
        movie = Movie.objects.get(id=response.data["id"])
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_create_movie_with_actors(self):
        actor_1 = sample_actor()
        actor_2 = sample_actor(last_name="Black")
        payload = {
            "title": "Test movie",
            "description": "Test description",
            "duration": 93,
            "actors": [actor_1.id, actor_2.id],
        }
        response = self.client.post(
            MOVIE_URL,
            data=payload
        )
        movie = Movie.objects.get(id=response.data["id"])
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        actors = movie.actors.all()
        self.assertIn(actor_1, actors)
        self.assertIn(actor_2, actors)
        self.assertEqual(len(actors), 2)

    def test_create_movie_with_genres(self):
        genre_1 = sample_genre()
        genre_2 = sample_genre(name="Horror")
        payload = {
            "title": "Test movie",
            "description": "Test description",
            "duration": 93,
            "genres": [genre_1.id, genre_2.id],
        }
        response = self.client.post(
            MOVIE_URL,
            data=payload
        )
        movie = Movie.objects.get(id=response.data["id"])
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        genres = movie.genres.all()
        self.assertIn(genre_1, genres)
        self.assertIn(genre_2, genres)
        self.assertEqual(len(genres), 2)

    def test_update_movie(self):
        movie = sample_movie()
        payload = {
            "description": "Test description",
        }
        url = detail_url(movie.id)
        response = self.client.patch(
            url,
            data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_movie(self):
        movie = sample_movie()
        url = detail_url(movie.id)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


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
