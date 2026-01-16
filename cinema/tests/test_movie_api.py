import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor
from cinema.serializers import MovieDetailSerializer

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


class UnauthenticatedMovieAPITests(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        result = self.client.get(MOVIE_URL)

        self.assertEqual(result.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthorizedMovieAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@myproject.com", password="test password"
        )
        self.client.force_authenticate(self.user)

    def test_movie_list(self):
        sample_movie()

        result = self.client.get(MOVIE_URL)
        self.assertEqual(result.status_code, status.HTTP_200_OK)

    def test_detail_movie_retrieve(self):
        movie = sample_movie()
        url = detail_url(movie.id)

        result = self.client.get(url)
        serializer = MovieDetailSerializer(movie)

        self.assertEqual(result.status_code, status.HTTP_200_OK)
        self.assertEqual(result.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Test Title",
            "description": "Test Description",
        }

        result = self.client.post(MOVIE_URL, payload)
        self.assertEqual(result.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@myproject.com",
            password="Test password",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)

    def test_movie_list(self):
        sample_movie()
        result = self.client.get(MOVIE_URL)

        self.assertEqual(result.status_code, status.HTTP_200_OK)

    def test_create_movie(self):
        genre = Genre.objects.create(name="Action")
        actors = Actor.objects.create(first_name="Tom", last_name="Hardy")
        payload = {
            "title": "Test Title",
            "description": "Test Description",
            "duration": 90,
            "genres": [genre.id],
            "actors": [actors.id],
        }
        result = self.client.post(MOVIE_URL, payload)

        self.assertEqual(result.status_code, status.HTTP_201_CREATED)

    def test_delete_movie(self):
        movie = sample_movie()
        url = detail_url(movie.id)
        result = self.client.delete(url)
        self.assertEqual(result.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class ListMovieFilterApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@myproject.com",
            password="Test password",
        )
        self.client.force_authenticate(self.user)

    def test_filter_movies_by_title(self):
        movie1 = Movie.objects.create(
            title="Matrix",
            description="Test Description",
            duration=90,
        )
        movie2 = Movie.objects.create(
            title="Save private Ryan",
            description="Test Description",
            duration=120,
        )

        result = self.client.get(MOVIE_URL, {"title": "Matrix"})

        self.assertEqual(result.status_code, status.HTTP_200_OK)
        self.assertIn(movie1.title, [movie["title"] for movie in result.data])
        self.assertNotIn(movie2.title, [movie["title"] for movie in result.data])

    def test_filter_movies_by_genres(self):
        genre1 = Genre.objects.create(name="Action")
        genre2 = Genre.objects.create(name="Horror")

        movie1 = Movie.objects.create(
            title="Matrix",
            description="Test Description",
            duration=90,
        )
        movie1.genres.add(genre1)

        movie2 = Movie.objects.create(
            title="Astral",
            description="Test Description",
            duration=120,
        )
        movie2.genres.add(genre2)

        movie3 = Movie.objects.create(
            title="Hostel",
            description="Test Description",
            duration=120,
        )
        movie3.genres.add(genre1, genre2)

        result = self.client.get(MOVIE_URL, {"genres": str(genre1.id)})
        self.assertEqual(result.status_code, status.HTTP_200_OK)
        titles = [movie["title"] for movie in result.data]
        self.assertIn("Matrix", titles)
        self.assertIn("Hostel", titles)
        self.assertNotIn("Astral", titles)

    def test_filter_movies_by_actors(self):
        actor1 = Actor.objects.create(
            first_name="Tom",
            last_name="Hardy",
        )
        actor2 = Actor.objects.create(
            first_name="Til",
            last_name="Schweiger",
        )

        movie1 = Movie.objects.create(
            title="Matrix",
            description="Test Description",
            duration=90,
        )
        movie1.actors.add(actor1)

        movie2 = Movie.objects.create(
            title="Astral",
            description="Test Description",
            duration=120,
        )
        movie2.actors.add(actor2)

        movie3 = Movie.objects.create(
            title="Hostel",
            description="Test Description",
            duration=120,
        )
        movie3.actors.add(actor1, actor2)

        result = self.client.get(MOVIE_URL, {"actors": str(actor1.id)})
        self.assertEqual(result.status_code, status.HTTP_200_OK)
        titles = [movie["title"] for movie in result.data]
        self.assertIn("Matrix", titles)
        self.assertIn("Hostel", titles)
        self.assertNotIn("Astral", titles)


class MovieImageUploadTest(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.user = get_user_model().objects.create_user(
            email="test@myproject.com",
            password="Test password",
        )
        self.client.force_authenticate(self.user)

        self.movie = sample_movie()

    def test_non_admin_cannot_upload_image(self):
        image = SimpleUploadedFile(
            "image.jpg",
            b"image",
            content_type="image/jpeg",
        )
        url = image_upload_url(self.movie.id)
        result = self.client.post(
            url,
            {"image": image},
            format="multipart",
        )

        self.assertEqual(result.status_code, status.HTTP_403_FORBIDDEN)
