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
    MovieSerializer
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


class UnauthenticatedUserMovieTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test that unauthenticated users can't access API"""

        response = self.client.get(MOVIE_URL)

        self.assertEqual(response.status_code, 401)


class AuthenticatedUserMovieTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test_user@test.com",
            password="complicated_password"
        )
        self.client.force_authenticate(self.user)

    def test_movie_list(self):
        """Test that authenticated users can access movie list"""

        movie1 = sample_movie(title="movie1")
        movie2 = sample_movie(title="movie2")
        genre1 = sample_genre(name="drama")
        genre2 = sample_genre(name="thriller")
        actor1 = sample_actor()
        movie1.actors.add(actor1)
        movie1.genres.add(genre1)
        movie2.actors.add(actor1)
        movie2.genres.add(genre2)
        serializer = MovieListSerializer(Movie.objects.all(), many=True)
        response = self.client.get(MOVIE_URL)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, serializer.data)

    def test_filter_movies_by_title(self):
        """Test that user can filter movies by title"""
        movie1 = sample_movie(title="movie1")
        movie2 = sample_movie(title="movie2")
        serializer_movie1 = MovieListSerializer(movie1)
        serializer_movie2 = MovieListSerializer(movie2)

        response = self.client.get(
            MOVIE_URL,
            {
                "title": "movie1"
            }
        )

        self.assertIn(serializer_movie1.data, response.data)
        self.assertNotIn(serializer_movie2.data, response.data)

    def test_filter_movies_by_genres(self):
        """Test that user can filter movies by genres"""
        movie1 = sample_movie(title="movie1")
        movie2 = sample_movie(title="movie2")
        genre1 = sample_genre(name="drama")
        genre2 = sample_genre(name="thriller")
        genre3 = sample_genre(name="sci-fi")
        movie1.genres.add(genre1)
        movie2.genres.set([genre2, genre3])
        serializer_movie1 = MovieListSerializer(movie1)
        serializer_movie2 = MovieListSerializer(movie2)

        response = self.client.get(
            MOVIE_URL,
            {
                "genres": f"{genre2.id},{genre3.id}"
            }
        )

        self.assertNotIn(serializer_movie1.data, response.data)
        self.assertIn(serializer_movie2.data, response.data)

    def test_filter_movies_by_actors(self):
        """Test that user can filter movies by actors"""
        movie1 = sample_movie(title="movie1")
        movie2 = sample_movie(title="movie2")
        actor1 = sample_actor(
            first_name="actor1",
            last_name="actor1"
        )
        actor2 = sample_actor(
            first_name="actor2",
            last_name="actor2"
        )
        movie1.actors.add(actor1)
        movie2.actors.add(actor2)
        serializer_movie1 = MovieListSerializer(movie1)
        serializer_movie2 = MovieListSerializer(movie2)

        response = self.client.get(
            MOVIE_URL,
            {
                "actors": f"{actor1.id}"
            }
        )

        self.assertNotIn(serializer_movie2.data, response.data)
        self.assertIn(serializer_movie1.data, response.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie(title="movie1")
        actor = sample_actor(
            first_name="actor1",
            last_name="actor1"
        )
        genre = sample_genre(name="some_genre")
        movie.actors.add(actor)
        movie.genres.add(genre)
        url = reverse(
            "cinema:movie-detail",
            kwargs={"pk": movie.id}
        )

        response = self.client.get(url)
        serializer = MovieDetailSerializer(movie)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "movie",
            "description": "movie_description",
            "duration": 444
        }

        response = self.client.post(MOVIE_URL, payload)
        self.assertEqual(response.status_code, 403)


class AdminUserMovieTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@admin.com",
            password="too_complicated_password",
            is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_movie_succesful(self):
        actor = sample_actor(
            first_name="test_actor",
            last_name="test_actor"
        )
        genre = sample_genre(name="test_genre")
        payload = {
            "title": "test movie",
            "description": "test movie description",
            "duration": 444,
            "genres": [
                genre.id
            ],
            "actors": [
                actor.id
            ]
        }
        serializer = MovieSerializer(data=payload)
        self.assertTrue(serializer.is_valid())
        response = self.client.post(MOVIE_URL, payload)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Movie.objects.all().count(), 1)
