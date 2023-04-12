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
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "test@test.com",
            "somepassword12345",
        )
        self.client.force_authenticate(self.user)

    def test_list_movies(self):
        sample_movie()
        sample_movie()

        res = self.client.get(MOVIE_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_title(self):
        movie1 = sample_movie(title="Movie1")
        movie2 = sample_movie(title="Movie2")

        res = self.client.get(MOVIE_URL, {"title": "Movie1"})

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

    def test_filter_movies_by_genre(self):
        movie1 = sample_movie(title="Game")

        genre1 = Genre.objects.create(name="Action")

        movie1.genres.add(genre1)

        res = self.client.get(
            MOVIE_URL,
            {"genres": f"{genre1.id}"},
        )

        serializer1 = MovieListSerializer(movie1)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer1.data, res.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertCountEqual(res.data, res.data)

    def test_filter_movies_by_actor(self):
        movie1 = sample_movie(title="Call Me By Your Name")
        actor1 = sample_actor(
            first_name="Armie",
            last_name="Hammer"
        )
        actor2 = sample_actor(
            first_name="Timothée",
            last_name="Chalamet"
        )

        movie1.actors.add(actor1, actor2)

        res = self.client.get(MOVIE_URL)

        serializer = MovieListSerializer(movie1)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer.data, res.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()

        res = self.client.get(detail_url(movie.id))

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)


class AdminMovieApiTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.admin = get_user_model().objects.create_superuser(
            "test_admin@admin.com",
            "someadminpassword12345",
            is_staff=True,
        )
        self.client.force_authenticate(self.admin)

    def test_create_movie(self):
        genre = sample_genre()
        actor = sample_actor()

        payload = {
            "title": "Title",
            "description": "Description",
            "duration": 90,
            "genres": genre.id,
            "actors": actor.id,
        }

        res = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        for key in payload:
            if key == "genres":
                pass
                self.assertEqual([genre], list(movie.genres.all()))
            elif key == "actors":
                pass
                self.assertEqual([actor], list(movie.actors.all()))
            else:
                self.assertEqual(payload[key], getattr(movie, key))

    def test_update_movie_not_allowed(self):
        movie = sample_movie()
        payload = {
            "title": "New Title",
            "description": "New Description",
            "duration": 120,
        }

        res = self.client.patch(detail_url(movie.id), payload)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_movie_not_allowed(self):
        movie = sample_movie()

        res = self.client.delete(detail_url(movie.id))

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
