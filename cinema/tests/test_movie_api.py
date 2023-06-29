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


class UnauthenticatedMovieApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin.user@cinema.com", "1qazcde3"
        )
        self.client.force_authenticate(self.user)

        self.movie1 = sample_movie(title="sample_movie1")
        self.movie2 = sample_movie(title="sample_movie2")
        self.movie3 = sample_movie(title="sample_movie3")
        self.movie4 = sample_movie(title="sample_movie4")

        self.genre1 = sample_genre(name="fantasy")
        self.genre2 = sample_genre(name="history")

        self.actor1 = sample_actor(first_name="test_name1", last_name="test_last1")
        self.actor2 = sample_actor(first_name="test_name2", last_name="test_last2")

        self.movie3.genres.add(self.genre1)
        self.movie4.genres.add(self.genre2)

        self.movie2.actors.add(self.actor1)
        self.movie4.actors.add(self.actor2)

        self.serializer1 = MovieListSerializer(self.movie1)
        self.serializer2 = MovieListSerializer(self.movie2)
        self.serializer3 = MovieListSerializer(self.movie3)
        self.serializer4 = MovieListSerializer(self.movie4)

    def test_movie_list(self):
        res = self.client.get(MOVIE_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_title(self):
        res = self.client.get(MOVIE_URL, {"title": "movie1"})

        self.assertIn(self.serializer1.data, res.data)
        self.assertNotIn(self.serializer2.data, res.data)
        self.assertNotIn(self.serializer3.data, res.data)
        self.assertNotIn(self.serializer4.data, res.data)

    def test_filter_movies_by_genre(self):
        res = self.client.get(MOVIE_URL, {"genres": "1,2"})

        self.assertNotIn(self.serializer1.data, res.data)
        self.assertNotIn(self.serializer2.data, res.data)
        self.assertIn(self.serializer3.data, res.data)
        self.assertIn(self.serializer4.data, res.data)

    def test_filter_movies_by_actor(self):
        res = self.client.get(MOVIE_URL, {"actors": "1,2"})

        self.assertNotIn(self.serializer1.data, res.data)
        self.assertIn(self.serializer2.data, res.data)
        self.assertNotIn(self.serializer3.data, res.data)
        self.assertIn(self.serializer4.data, res.data)

    def test_movie_retrieve(self):
        url = reverse("cinema:movie-detail", args=[self.movie4.id])
        res = self.client.get(url)

        serializer = MovieDetailSerializer(self.movie4)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Sample movie",
            "description": "Sample description",
            "duration": 90,
        }

        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_movie_forbidden(self):
        payload = {
            "title": "sample_movie1 1",
        }

        url = reverse("cinema:movie-detail", args=[self.movie3.id])
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_movie_forbidden(self):
        url = reverse("cinema:movie-detail", args=[self.movie3.id])
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
