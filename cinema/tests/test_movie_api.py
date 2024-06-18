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


def sample_movie(**params) -> Movie:
    defaults = {
        "title": "Sample movie",
        "description": "Sample description",
        "duration": 90,
    }
    defaults.update(params)

    return Movie.objects.create(**defaults)


def sample_genre(**params) -> Genre:
    defaults = {
        "name": "Drama",
    }
    defaults.update(params)

    return Genre.objects.create(**defaults)


def sample_actor(**params) -> Actor:
    defaults = {"first_name": "George", "last_name": "Clooney"}
    defaults.update(params)

    return Actor.objects.create(**defaults)


def sample_movie_session(**params) -> MovieSession:
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


def movie_detail_url(movie_id) -> str:
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
        res = self.client.get(movie_detail_url(self.movie.id))

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

    def test_list_auth_required(self) -> None:
        response = self.client.get(MOVIE_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        response = self.client.post(MOVIE_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_details_auth_required(self) -> None:
        movie = sample_movie()
        movie_url = movie_detail_url(movie.id)
        response = self.client.get(movie_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        response = self.client.post(movie_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedUserMovieApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "user@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)
        self.movie_with_all_data = sample_movie()
        self.movie_without_data = sample_movie(
            title="test title",
            description="test description",
            duration=60
        )
        self.genre = sample_genre()
        self.actor = sample_actor()
        self.movie_with_all_data.genres.add(self.genre)
        self.movie_with_all_data.actors.add(self.actor)

    def test_list_user_get(self) -> None:

        response = self.client.get(MOVIE_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.data, serializer.data)

    def test_filter_movies(self) -> None:
        response_title = self.client.get(
            MOVIE_URL,
            {"title": self.movie_with_all_data.title}
        )
        response_actors = self.client.get(
            MOVIE_URL,
            {"actors": f"{self.actor.id}"}
        )
        response_genres = self.client.get(
            MOVIE_URL,
            {"genres": f"{self.genre.id}"}
        )
        serializer_with_data = MovieListSerializer(self.movie_with_all_data)
        serializer_without_data = MovieListSerializer(self.movie_without_data)

        for response in (
            response_title,
            response_actors,
            response_genres
        ):
            self.assertIn(serializer_with_data.data, response.data)
            self.assertNotIn(serializer_without_data.data, response.data)

    def test_list_user_post(self) -> None:
        response = self.client.post(MOVIE_URL)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_detail_user_retrieve(self) -> None:
        url = movie_detail_url(self.movie_with_all_data.id)
        response = self.client.get(url)

        serializer = MovieDetailSerializer(self.movie_with_all_data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)


class AdminMovieApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)
        self.movie_with_all_data = sample_movie()
        self.movie_without_data = sample_movie(
            title="test title",
            description="test description",
            duration=60
        )
        self.genre = sample_genre()
        self.actor = sample_actor()
        self.movie_with_all_data.genres.add(self.genre)
        self.movie_with_all_data.actors.add(self.actor)

    def test_list_admin_post(self) -> None:
        payload = {
            "title": "test movie",
            "description": "test description",
            "duration": 99,
            "genres": 1,
            "actors": 1
        }

        response = self.client.post(MOVIE_URL, data=payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_delete_not_allowed(self) -> None:
        url = movie_detail_url(self.movie_with_all_data.id)
        response = self.client.delete(url)

        self.assertEqual(
            response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )
