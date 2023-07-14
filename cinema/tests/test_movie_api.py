import shutil
import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor
from cinema.serializers import MovieDetailSerializer, MovieListSerializer

MOVIE_URL = reverse("cinema:movie-list")
MOVIE_SESSION_URL = reverse("cinema:moviesession-list")

TEST_DIR = 'test_data'


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
        shutil.rmtree(TEST_DIR, ignore_errors=True)

    @override_settings(MEDIA_ROOT=(TEST_DIR + '/media'))
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

    @override_settings(MEDIA_ROOT=(TEST_DIR + '/media'))
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

    @override_settings(MEDIA_ROOT=(TEST_DIR + '/media'))
    def test_image_url_is_shown_on_movie_detail(self):
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(detail_url(self.movie.id))

        self.assertIn("image", res.data)

    @override_settings(MEDIA_ROOT=(TEST_DIR + '/media'))
    def test_image_url_is_shown_on_movie_list(self):
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(MOVIE_URL)

        self.assertIn("image", res.data[0].keys())

    @override_settings(MEDIA_ROOT=(TEST_DIR + '/media'))
    def test_image_url_is_shown_on_movie_session_detail(self):
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(MOVIE_SESSION_URL)

        self.assertIn("movie_image", res.data[0].keys())


class UnauthenticatedMovieAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "user@test.com",
            "user12345",
        )
        self.client.force_authenticate(self.user)

        self.movie_1 = sample_movie(title="The Godfather")
        self.movie_2 = sample_movie(title="The Thing")
        self.movie_3 = sample_movie(title="Soul")

        self.genre_1 = sample_genre(name="Drama")
        self.genre_2 = sample_genre(name="Sci-Fi")
        self.genre_3 = sample_genre(name="Animation")

        self.movie_1.genres.add(self.genre_1)
        self.movie_2.genres.add(self.genre_2)
        self.movie_3.genres.add(self.genre_3)

        self.actor_1 = sample_actor(first_name="Marlon", last_name="Brando")
        self.actor_2 = sample_actor(first_name="Keith", last_name="David")
        self.actor_3 = sample_actor(first_name="Tina", last_name="Fey")

        self.movie_1.actors.add(self.actor_1)
        self.movie_2.actors.add(self.actor_2)
        self.movie_3.actors.add(self.actor_3)

        self.serializer_1 = MovieListSerializer(self.movie_1)
        self.serializer_2 = MovieListSerializer(self.movie_2)
        self.serializer_3 = MovieListSerializer(self.movie_3)

    def test_list_movie(self):
        res = self.client.get(MOVIE_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_title(self):
        res = self.client.get(MOVIE_URL, {"title": "The"})

        self.assertIn(self.serializer_1.data, res.data)
        self.assertIn(self.serializer_2.data, res.data)
        self.assertNotIn(self.serializer_3.data, res.data)

    def test_filter_movies_by_genres(self):
        res = self.client.get(
            MOVIE_URL, {"genres": f"{self.genre_1.id},{self.genre_2.id}"}
        )

        self.assertIn(self.serializer_1.data, res.data)
        self.assertIn(self.serializer_2.data, res.data)
        self.assertNotIn(self.serializer_3.data, res.data)

    def test_filter_movies_by_actors(self):
        res = self.client.get(
            MOVIE_URL, {"actors": f"{self.actor_1.id},{self.actor_2.id}"}
        )

        self.assertIn(self.serializer_1.data, res.data)
        self.assertIn(self.serializer_2.data, res.data)
        self.assertNotIn(self.serializer_3.data, res.data)

    def test_retrieve_movie_detail(self):
        url = detail_url(self.movie_1.id)
        res = self.client.get(url)

        serializer = MovieDetailSerializer(self.movie_1)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "The Matrix",
            "duration": 136,
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "user@test.com",
            "user12345",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        genre_1 = sample_genre(name="Sci-Fi")
        genre_2 = sample_genre(name="Action")

        actor = sample_actor(first_name="Keanu", last_name="Reeves")

        payload = {
            "title": "The Matrix",
            "description": "The Matrix",
            "duration": 136,
            "genres": [genre_1.id, genre_2.id],
            "actors": [actor.id],
        }

        res = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        for field in ["title", "description", "duration"]:
            self.assertEqual(payload[field], getattr(movie, field))
        self.assertIn(genre_1, movie.genres.all())
        self.assertIn(genre_2, movie.genres.all())
        self.assertIn(actor, movie.actors.all())
