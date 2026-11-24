import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor

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
        self.normal_user = get_user_model().objects.create_user(
            "user@myproject.com", "password"
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
                    "genres": [self.genre.id],
                    "actors": [self.actor.id],
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

    def test_anonymous_post_image(self):
        self.client.force_authenticate(user=None)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(image_upload_url(
                self.movie.id),
                {"image": ntf},
                format="multipart"
            )
            self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_post_image(self):
        self.client.force_authenticate(user=self.normal_user)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(image_upload_url(
                self.movie.id),
                {"image": ntf},
                format="multipart"
            )
            self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class MovieViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "user@myproject.com", "password"
        )
        self.admin_user = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        self.movie = sample_movie()
        self.genre = sample_genre()
        self.movie.genres.add(self.genre)
        self.actor = sample_actor()
        self.movie.actors.add(self.actor)
        self.movie_session = sample_movie_session(movie=self.movie)

    def test_anonymous_user_get(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_get(self):
        self.client.force_authenticate(user=self.user)
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_admin_user_get(self):
        self.client.force_authenticate(user=self.admin_user)
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_anonymous_user_post(self):
        res = self.client.post(MOVIE_URL, {
            "title": "Title",
            "description": "Description",
            "duration": 90
        })
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_post(self):
        self.client.force_authenticate(user=self.user)
        res = self.client.post(MOVIE_URL, {
            "title": "Title",
            "description": "Description",
            "duration": 90
        })
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_post(self):
        self.client.force_authenticate(user=self.admin_user)
        res = self.client.post(MOVIE_URL, {
            "title": "Title",
            "description": "Description",
            "duration": 90,
            "genres": [self.genre.id],
            "actors": [self.actor.id]
        })
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Movie.objects.filter(title="Title").exists())

    def test_anonymous_user_get_retrieve(self):
        res = self.client.get(detail_url(self.movie.id))
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_get_retrieve(self):
        self.client.force_authenticate(user=self.user)
        res = self.client.get(detail_url(self.movie.id))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_admin_user_get_retrieve(self):
        self.client.force_authenticate(user=self.admin_user)
        res = self.client.get(detail_url(self.movie.id))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_filter_movies_by_title(self):
        self.client.force_authenticate(user=self.user)
        sample_movie(title="Another Movie")
        res = self.client.get(MOVIE_URL, {"title": "Sample"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], "Sample movie")

    def test_filter_movies_by_genre(self):
        self.client.force_authenticate(user=self.user)
        res = self.client.get(MOVIE_URL, {"genres": [self.genre.id]})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data[0]["genres"], ["Drama"])

    def test_filter_movies_by_unassigned_genre(self):
        self.client.force_authenticate(user=self.user)
        comedy = sample_genre(name="Comedy")
        res = self.client.get(MOVIE_URL, {"genres": [comedy.id]})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, [])

    def test_filter_movies_by_actor(self):
        self.client.force_authenticate(user=self.user)
        res = self.client.get(MOVIE_URL, {"actors": [self.actor.id]})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data[0]["actors"], ["George Clooney"])

    def test_filter_movies_by_unassigned_actor(self):
        self.client.force_authenticate(user=self.user)
        wick = sample_actor(first_name="John", last_name="Wick")
        res = self.client.get(MOVIE_URL, {"actors": [wick.id]})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, [])
