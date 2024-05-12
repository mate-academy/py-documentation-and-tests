import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

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


class UnAuthenticatedMovieApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        result = self.client.get(MOVIE_URL)

        self.assertEqual(result.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@user.com", password="1qazcde3"
        )
        self.client.force_authenticate(self.user)

    def test_list_movies(self):
        sample_movie()
        movie_with_genres = sample_movie()

        genre1 = Genre.objects.create(name="Action")
        genre2 = Genre.objects.create(name="Drama")

        movie_with_genres.genres.add(genre1, genre2)

        result = self.client.get(MOVIE_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(result.status_code, status.HTTP_200_OK)
        self.assertEqual(result.data, serializer.data)

    def test_filter_movies_actors(self):
        movie1 = sample_movie(title="My Bloody Valentine")
        movie2 = sample_movie(title="Supernatural")

        actor1 = Actor.objects.create(first_name="Jensen", last_name="Ackles")
        actor2 = Actor.objects.create(first_name="Jared", last_name="Padalecki")

        movie1.actors.add(actor1)
        movie2.actors.add(actor2)
        movie3 = sample_movie(title="Movie with no actor")

        result = self.client.get(
            MOVIE_URL, data={"actors": f"{actor1.id}, {actor2.id}"}
        )

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie3)

        self.assertIn(serializer1.data, result.data)
        self.assertIn(serializer2.data, result.data)
        self.assertNotIn(serializer3.data, result.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        genre = Genre.objects.create(name="Drama")

        movie.genres.add(genre)

        url = detail_url(movie_id=movie.id)
        result = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(result.status_code, status.HTTP_200_OK)
        self.assertEqual(result.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Supernatural",
            "description": "Story about two brothers...",
            "duration": 45,
        }

        result = self.client.post(MOVIE_URL, payload)

        self.assertEqual(result.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@admin.com", password="1qazcde3", is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        payload = {
            "title": "Supernatural",
            "description": "Story about two brothers...",
            "duration": 54,
        }

        result = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=result.data["id"])

        self.assertEqual(result.status_code, status.HTTP_201_CREATED)
        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def create_movie_with_genres(self):
        genre1 = Genre.objects.create(name="Action")
        genre2 = Genre.objects.create(name="Drama")

        payload = {
            "title": "Supernatural",
            "description": "Story about two brothers...",
            "duration": 54,
            "genres": [genre1.id, genre2.id],
        }

        result = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=result.data["id"])
        genres = movie.genres.all()

        self.assertEqual(result.status_code, status.HTTP_201_CREATED)
        self.assertEqual(genres.count(), 2)
        self.assertIn(genre1, genres)
        self.assertIn(genre2, genres)

    def test_delete_movie_not_allow(self):
        movie = sample_movie()

        url = detail_url(movie_id=movie.id)

        result = self.client.delete(url)

        self.assertEqual(result.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
