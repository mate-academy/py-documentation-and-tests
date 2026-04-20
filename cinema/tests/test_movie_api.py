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
    MovieSerializer,
    MovieListSerializer,
    MovieDetailSerializer
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


class UnauthorizedMovieApiTests(TestCase):

    def test_authorization_required(self) -> None:
        response = self.client.get(MOVIE_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthorizedMovieApiTests(TestCase):

    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user@cinema.test",
            password="testpass1234"
        )
        self.client.force_authenticate(self.user)

    def test_movie_list(self) -> None:
        sample_movie()
        sample_movie()
        response = self.client.get(MOVIE_URL)
        serializer = MovieListSerializer(Movie.objects.all(), many=True)

        self.assertEqual(serializer.data, response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_movie_retrieve(self) -> None:
        movie = sample_movie()

        response = self.client.get(detail_url(movie.id))
        serializer = MovieDetailSerializer(movie)

        self.assertEqual(serializer.data, response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_movie_is_forbidden(self) -> None:
        data = {
            "title": "Test title",
            "description": "Test description",
            "duration": 100
        }
        response = self.client.post(MOVIE_URL, data=data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_filter_movie_by_title(self) -> None:
        movie_1 = sample_movie(title="Movie 1")
        movie_2 = sample_movie(title="Test Movie 2")

        response = self.client.get(
            MOVIE_URL,
            query_params={"title": "Test movie"}
        )

        serializer_not_for_filter = MovieDetailSerializer(movie_1)
        serializer_for_filter = MovieDetailSerializer(movie_2)

        self.assertNotIn(serializer_not_for_filter.data, response.data)
        self.assertIn(serializer_for_filter.data, response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_filter_movie_by_genres(self) -> None:
        genre_1 = sample_genre()
        genre_2 = sample_genre(name="Test genre")

        movie_1 = sample_movie()
        movie_1.genres.add(genre_1)
        movie_2 = sample_movie(title="Test movie")
        movie_2.genres.add(genre_2)

        response = self.client.get(
            MOVIE_URL,
            query_params={"genres": f"{genre_1.id}"}
        )

        serializer_1 = MovieListSerializer(movie_1)
        serializer_2 = MovieListSerializer(movie_2)

        self.assertIn(serializer_1.data, response.data)
        self.assertNotIn(serializer_2.data, response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_filter_movie_by_actors(self) -> None:
        actor_1 = sample_actor()
        actor_2 = sample_actor(first_name="Test first", last_name="Test last")

        movie_1 = sample_movie()
        movie_1.actors.add(actor_1)
        movie_2 = sample_movie(title="Test movie")
        movie_2.actors.add(actor_2)

        response = self.client.get(
            MOVIE_URL,
            query_params={"actors": f"{actor_2.id}"}
        )

        serializer_1 = MovieListSerializer(movie_1)
        serializer_2 = MovieListSerializer(movie_2)

        self.assertNotIn(serializer_1.data, response.data)
        self.assertIn(serializer_2.data, response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class AdminMovieApiTests(TestCase):

    def setUp(self) -> None:
        self.client = APIClient()
        self.super_user = get_user_model().objects.create_superuser(
            email="admin@cinema.test",
            password="testpass1234"
        )
        self.client.force_authenticate(self.super_user)

    def test_create_movie(self) -> None:
        actor = sample_actor()
        genre = sample_genre()
        data = {
            "title": "Test title",
            "description": "Test description",
            "duration": 120,
            "genres": (genre.id, ),
            "actors": (actor.id, ),
        }

        response = self.client.post(MOVIE_URL, data=data)

        movie = Movie.objects.get(id=response.data["id"])
        serializer = MovieSerializer(movie)

        self.assertEqual(serializer.data, response.data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_update_movie_not_allowed(self) -> None:
        data = {
            "title": "Test title",
            "description": "Test description",
            "duration": 300
        }
        response = self.client.put(detail_url(sample_movie().id), data=data)

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def test_partial_update_movie_not_allowed(self) -> None:
        response = self.client.patch(detail_url(
            sample_movie().id),
            data={"duration": 180}
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def test_destroy_movie_not_allowed(self) -> None:
        response = self.client.delete(detail_url(sample_movie().id))

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED
        )


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
