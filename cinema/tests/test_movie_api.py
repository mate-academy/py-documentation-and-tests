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
    MovieDetailSerializer,
    MovieListSerializer,
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


class MovieUnauthorizedUserTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_movie_list_auth_required(self):
        response = self.client.get(MOVIE_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_movie_detail_auth_required(self):
        movie = sample_movie()
        response = self.client.get(detail_url(movie.id))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class MovieAuthorizedUserTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@test.com", "testpassword123"
        )
        self.client.force_authenticate(self.user)

    def test_list_movie(self):
        sample_movie()
        movie_with_params = sample_movie()

        movie_with_params.genres.add(sample_genre())
        movie_with_params.actors.add(sample_actor())

        response = self.client.get(MOVIE_URL)

        movie = Movie.objects.all()
        serializer = MovieListSerializer(movie, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_filtered_movies(self):
        movie = sample_movie()
        movie_with_params = sample_movie()

        actor = sample_actor()
        genre = sample_genre()

        movie_with_params.actors.add(actor)
        movie_with_params.genres.add(genre)

        response1 = self.client.get(MOVIE_URL, {"actors": f"{actor.id}"})
        response2 = self.client.get(MOVIE_URL, {"genres": f"{genre.id}"})
        response3 = self.client.get(MOVIE_URL, {"title": f"{movie_with_params.title}"})

        serializer1 = MovieListSerializer(movie_with_params)
        serializer2 = MovieListSerializer(movie)

        self.assertIn(serializer1.data, response1.data)
        self.assertNotIn(serializer2.data, response1.data)

        self.assertIn(serializer1.data, response2.data)
        self.assertNotIn(serializer2.data, response2.data)

        self.assertIn(serializer1.data, response3.data)
        self.assertIn(serializer2.data, response3.data)

    def test_retrieve_movie(self):
        movie_with_params = sample_movie()

        movie_with_params.genres.add(sample_genre())
        movie_with_params.actors.add(sample_actor())

        response = self.client.get(detail_url(movie_with_params.id))

        serializer = MovieDetailSerializer(movie_with_params)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_create_movie(self):
        movie_params = {
            "title": "Sample movie",
            "description": "Sample description",
            "duration": 90,
        }

        response = self.client.post(MOVIE_URL, movie_params)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_movie(self):
        movie = sample_movie()

        params_to_put = {
            "title": "Sample movie",
            "description": "Sample description",
            "duration": 90,
        }
        params_to_patch = {
            "title": "Sample movie",
        }

        response1 = self.client.put(detail_url(movie.id), params_to_put)
        response2 = self.client.patch(detail_url(movie.id), params_to_patch)

        self.assertEqual(response1.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response2.status_code, status.HTTP_403_FORBIDDEN)


class MovieAdminUserTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "test@test.com", "testpassword123"
        )
        self.client.force_authenticate(self.user)

    def test_admin_create_movie(self):
        sample_actor()
        sample_genre()
        movie_params = {
            "title": "Sample movie",
            "description": "Sample description",
            "duration": 90,
            "actors": 1,
            "genres": 1,
        }

        response = self.client.post(MOVIE_URL, movie_params)
        print(response.data)

        movie = Movie.objects.get(pk=response.data["id"])
        serializer = MovieSerializer(movie)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(serializer.data, response.data)

    def test_admin_update_movie_not_allowed(self):
        movie = sample_movie()

        params_to_put = {
            "title": "Sample movie",
            "description": "Sample description",
            "duration": 90,
        }
        params_to_patch = {
            "title": "Sample movie",
        }

        response1 = self.client.put(detail_url(movie.id), params_to_put)
        response2 = self.client.patch(detail_url(movie.id), params_to_patch)

        self.assertEqual(response1.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(response2.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_admin_delete_movie_not_allowed(self):
        movie = sample_movie()

        response = self.client.delete(detail_url(movie.id))

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
