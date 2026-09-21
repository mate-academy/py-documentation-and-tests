import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.core.cache import cache
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
        cache.clear()
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


class PublicMovieApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()

    def test_authentication_is_required(self):
        response = self.client.get(MOVIE_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateMovieApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user(
            email="user@example.com",
            password="testpass123",
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

        self.action = sample_genre(name="Action")
        self.drama = sample_genre(name="Drama")
        self.first_actor = sample_actor(
            first_name="First",
            last_name="Actor",
        )
        self.second_actor = sample_actor(
            first_name="Second",
            last_name="Actor",
        )

        self.first_movie = sample_movie(title="Alpha Movie")
        self.first_movie.genres.add(self.action)
        self.first_movie.actors.add(self.first_actor)

        self.second_movie = sample_movie(title="Beta Story")
        self.second_movie.genres.add(self.drama)
        self.second_movie.actors.add(self.second_actor)

    def test_list_movies(self):
        response = self.client.get(MOVIE_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_retrieve_movie(self):
        response = self.client.get(detail_url(self.first_movie.id))
        serializer = MovieDetailSerializer(self.first_movie)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_filter_movies_by_title(self):
        response = self.client.get(MOVIE_URL, {"title": "alpha"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [movie["id"] for movie in response.data],
            [self.first_movie.id],
        )

    def test_filter_movies_by_genres(self):
        response = self.client.get(
            MOVIE_URL,
            {"genres": f"{self.action.id},{self.drama.id}"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            {movie["id"] for movie in response.data},
            {self.first_movie.id, self.second_movie.id},
        )

    def test_filter_movies_by_actors(self):
        response = self.client.get(
            MOVIE_URL,
            {"actors": str(self.second_actor.id)},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [movie["id"] for movie in response.data],
            [self.second_movie.id],
        )

    def test_regular_user_cannot_create_movie(self):
        response = self.client.post(
            MOVIE_URL,
            {
                "title": "New Movie",
                "description": "Description",
                "duration": 100,
                "genres": [self.action.id],
                "actors": [self.first_actor.id],
            },
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.admin = get_user_model().objects.create_superuser(
            email="admin@example.com",
            password="testpass123",
        )
        self.client = APIClient()
        self.client.force_authenticate(self.admin)
        self.genre = sample_genre(name="Comedy")
        self.actor = sample_actor(
            first_name="Admin",
            last_name="Actor",
        )

    def test_admin_can_create_movie(self):
        payload = {
            "title": "Created Movie",
            "description": "Description",
            "duration": 110,
            "genres": [self.genre.id],
            "actors": [self.actor.id],
        }

        response = self.client.post(MOVIE_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(id=response.data["id"])
        self.assertEqual(movie.title, payload["title"])
        self.assertEqual(list(movie.genres.all()), [self.genre])
        self.assertEqual(list(movie.actors.all()), [self.actor])

    def test_update_and_delete_are_not_available(self):
        movie = sample_movie()
        url = detail_url(movie.id)

        update_response = self.client.patch(url, {"title": "Changed"})
        delete_response = self.client.delete(url)

        self.assertEqual(
            update_response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )
        self.assertEqual(
            delete_response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )
