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


class UnauthenticatedMovieApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        result = self.client.get(MOVIE_URL)

        self.assertEqual(result.status_code, status.HTTP_401_UNAUTHORIZED)


@override_settings(
    REST_FRAMEWORK={
        "DEFAULT_THROTTLE_CLASSES": [],
        "DEFAULT_THROTTLE_RATES": {
            "anon": None,
            "user": None
        }
    }
)
class AuthenticatedMovieApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "user@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)

        self.movie_sample = sample_movie()
        self.movie_inception = sample_movie(title="Inception")
        self.movie_looper = sample_movie(title="Looper")
        self.genre_sample = sample_genre()
        self.genre_mystery = sample_genre(name="Mystery")
        self.genre_action = sample_genre(name="Action")
        self.actor_sample = sample_actor()
        self.actor_elliot = sample_actor(
            first_name="Elliot",
            last_name="Page"
        )
        self.actor_matt = sample_actor(
            first_name="Matt",
            last_name="Damon"
        )
        self.movie_sample.genres.add(self.genre_sample)
        self.movie_inception.genres.add(self.genre_mystery)
        self.movie_looper.genres.add(self.genre_action)
        self.movie_sample.actors.add(self.actor_sample)
        self.movie_inception.actors.add(self.actor_elliot)
        self.movie_looper.actors.add(self.actor_matt)

    def test_get_movies_list(self):
        result = self.client.get(MOVIE_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(result.status_code, status.HTTP_200_OK)
        self.assertEqual(result.data, serializer.data)
        self.assertEqual(len(result.data), len(serializer.data))

    def test_filter_movies_by_title(self):
        result = self.client.get(
            MOVIE_URL,
            {"title": "looper"}
        )

        movie = Movie.objects.filter(title__icontains="looper")
        serializer = MovieListSerializer(movie, many=True)

        self.assertEqual(result.status_code, status.HTTP_200_OK)
        self.assertEqual(result.data, serializer.data)
        self.assertEqual(len(result.data), len(serializer.data))

    def test_filter_movies_by_genres(self):
        result = self.client.get(
            MOVIE_URL,
            {"genres": f"{self.genre_sample.id},{self.genre_mystery.id}"}
        )

        serializer_movie_genre_sample = MovieListSerializer(self.movie_sample)
        serializer_movie_genre_mystery = MovieListSerializer(self.movie_inception)
        serializer_movie_genre_action = MovieListSerializer(self.movie_looper)

        self.assertEqual(result.status_code, status.HTTP_200_OK)
        self.assertIn(serializer_movie_genre_sample.data, result.data)
        self.assertIn(serializer_movie_genre_mystery.data, result.data)
        self.assertNotIn(serializer_movie_genre_action.data, result.data)

    def test_filter_movies_by_actors(self):
        result = self.client.get(
            MOVIE_URL,
            {"actors": f"{self.actor_elliot.id},{self.actor_matt.id}"}
        )

        serializer_movie_actor_sample = MovieListSerializer(self.movie_sample)
        serializer_movie_actor_elliot = MovieListSerializer(self.movie_inception)
        serializer_movie_actor_matt = MovieListSerializer(self.movie_looper)

        self.assertEqual(result.status_code, status.HTTP_200_OK)
        self.assertIn(serializer_movie_actor_elliot.data, result.data)
        self.assertIn(serializer_movie_actor_matt.data, result.data)
        self.assertNotIn(serializer_movie_actor_sample.data, result.data)

    def test_retrieve_movie_detail(self):
        url = detail_url(self.movie_sample.id)
        result = self.client.get(url)

        serializer = MovieDetailSerializer(self.movie_sample)

        self.assertEqual(result.status_code, status.HTTP_200_OK)
        self.assertEqual(result.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Sample movie",
            "description": "Sample description",
            "duration": 90,
        }

        result = self.client.post(MOVIE_URL, payload)

        self.assertEqual(result.status_code, status.HTTP_403_FORBIDDEN)


@override_settings(
    REST_FRAMEWORK={
        "DEFAULT_THROTTLE_CLASSES": [],
        "DEFAULT_THROTTLE_RATES": {
            "anon": None,
            "user": None
        }
    }
)
class AdminMovieTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@myproject.com",
            password="password",
            is_staff=True
        )
        self.client.force_authenticate(self.user)

        self.movie_sample = sample_movie()
        self.movie_inception = sample_movie(title="Inception")
        self.movie_looper = sample_movie(title="Looper")
        self.genre_sample = sample_genre()
        self.genre_mystery = sample_genre(name="Mystery")
        self.genre_action = sample_genre(name="Action")
        self.actor_sample = sample_actor()
        self.actor_elliot = sample_actor(
            first_name="Elliot",
            last_name="Page"
        )
        self.actor_matt = sample_actor(
            first_name="Matt",
            last_name="Damon"
        )
        self.movie_sample.genres.add(self.genre_sample)
        self.movie_inception.genres.add(self.genre_mystery)
        self.movie_looper.genres.add(self.genre_action)
        self.movie_sample.actors.add(self.actor_sample)
        self.movie_inception.actors.add(self.actor_elliot)
        self.movie_looper.actors.add(self.actor_matt)

    def test_create_movie(self):
        payload = {
            "title": "Some Movie",
            "description": "Some description",
            "duration": 90,
        }

        result = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(id=result.data["id"])

        self.assertEqual(result.status_code, status.HTTP_201_CREATED)

        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_delete_movie_not_allowed(self):
        url = detail_url(self.movie_sample.id)

        result = self.client.delete(url)

        self.assertEqual(result.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
