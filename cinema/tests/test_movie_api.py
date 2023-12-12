import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor
from cinema.serializers import (
    MovieListSerializer,
    MovieDetailSerializer,
)

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
    cinema_hall = CinemaHall.objects.create(name="Blue", rows=20, seats_in_row=20)

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


class UnauthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(MOVIE_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="testemail@test.com", password="testpassword1234"
        )
        self.client.force_authenticate(self.user)

    def test_list_movies(self):
        sample_movie()
        sample_movie()

        response = self.client.get(MOVIE_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_filter_movies_by_genres(self):
        genre = sample_genre(name="Test genre")

        matched_movie = sample_movie(title="Movie with genre")
        mismatched_movie = sample_movie(title="Movie without genre")

        matched_movie.genres.add(genre)

        response = self.client.get(MOVIE_URL, data={"genres": f"{genre.id}"})
        matched_movie_serializer = MovieListSerializer(matched_movie)
        mismatched_movie_serializer = MovieListSerializer(mismatched_movie)

        self.assertIn(matched_movie_serializer.data, response.data)
        self.assertNotIn(mismatched_movie_serializer.data, response.data)

    def test_filter_movies_by_actors(self):
        actor = sample_actor(first_name="Test")

        matched_movie = sample_movie(title="Movie with test actor")
        mismatched_movie = sample_movie(title="Movie without test actor")

        matched_movie.actors.add(actor)

        res = self.client.get(MOVIE_URL, data={"actors": f"{actor.id}"})
        matched_movie_serializer = MovieListSerializer(matched_movie)
        mismatched_movie_serializer = MovieListSerializer(mismatched_movie)

        self.assertIn(matched_movie_serializer.data, res.data)
        self.assertNotIn(mismatched_movie_serializer.data, res.data)

    def test_filter_movies_by_title(self):
        matched_movie = sample_movie(title="Test movie title")
        mismatched_movie = sample_movie(title="Movie title")

        response = self.client.get(MOVIE_URL, data={"title": "test"})
        matched_movie_serializer = MovieListSerializer(matched_movie)
        mismatched_movie_serializer = MovieListSerializer(mismatched_movie)

        self.assertIn(matched_movie_serializer.data, response.data)
        self.assertNotIn(mismatched_movie_serializer.data, response.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie(title="Test movie")
        genre = sample_genre(name="Test genre")

        movie.genres.add(genre)

        url = detail_url(movie.id)
        response = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Test movie",
            "description": "Test movie description",
            "duration": 75,
        }
        response = self.client.post(MOVIE_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.admin_user = get_user_model().objects.create_user(
            email="testemail@test.com",
            password="testpassword1234",
            is_staff=True,
        )
        self.client.force_authenticate(self.admin_user)

    def test_create_movie(self):
        genre = sample_genre(name="genre")
        actor = sample_actor(first_name="Test")

        payload = {
            "title": "Test movie",
            "description": "Test movie description",
            "duration": 75,
            "genres": [genre.id],
            "actors": [actor.id],
        }

        response = self.client.post(
            MOVIE_URL,
            data=payload,
        )
        movie = Movie.objects.get(id=response.data["id"])

        genres = movie.genres.all()
        actors = movie.actors.all()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertIn(genre, genres)
        self.assertEqual(genres.count(), 1)

        self.assertIn(actor, actors)
        self.assertEqual(actors.count(), 1)

    def test_delete_movie_forbidden(self):
        movie = sample_movie()

        url = detail_url(movie.id)
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
