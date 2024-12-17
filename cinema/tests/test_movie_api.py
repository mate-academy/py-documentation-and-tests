import os
import tempfile

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from PIL import Image
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from cinema.models import Actor, CinemaHall, Genre, Movie, MovieSession

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

class MovieViewSetTest(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.genre1 = Genre.objects.create(name="Drama")
        self.genre2 = Genre.objects.create(name="Action")

        self.actor1 = Actor.objects.create(first_name="Michael", last_name="Johnson")
        self.actor2 = Actor.objects.create(first_name="Emma", last_name="Brown")

        self.movie1 = Movie.objects.create(
            title="The Silent Road", description="A drama about resilience", duration=110
        )
        self.movie1.genres.add(self.genre1)
        self.movie1.actors.add(self.actor1)

        self.movie2 = Movie.objects.create(
            title="Chasing Shadows", description="An action-packed thriller", duration=95
        )
        self.movie2.genres.add(self.genre2)
        self.movie2.actors.add(self.actor2)

        self.list_url = reverse("cinema:movie-list")
        self.detail_url = lambda pk: reverse("cinema:movie-detail", args=[pk])

        self.admin_user = get_user_model().objects.create_superuser(
            email="admin@example.com",
            password="password123",
        )
        self.regular_user = get_user_model().objects.create_user(
            email="user@example.com",
            password="password123",
        )

    def test_list_movies(self):
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_list_movies_with_filter(self):
        self.client.force_authenticate(user=self.regular_user)

        response = self.client.get(self.list_url, {"title": "The Silent Road"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "The Silent Road")

        response = self.client.get(self.list_url, {"genres": str(self.genre1.id)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "The Silent Road")

    def test_retrieve_movie_detail(self):
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get(self.detail_url(self.movie1.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "The Silent Road")
        self.assertEqual(response.data["genres"][0]["name"], "Drama")
        self.assertEqual(response.data["actors"][0]["full_name"], "Michael Johnson")

    def test_create_movie(self):
        self.client.force_authenticate(user=self.admin_user)
        payload = {
            "title": "Lost in Time",
            "description": "A thrilling adventure through time",
            "duration": 130,
            "genres": [self.genre1.id],
            "actors": [self.actor1.id, self.actor2.id],
        }
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["title"], "Lost in Time")

    def test_filter_movies_by_actor(self):
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get(self.list_url, {"actors": str(self.actor1.id)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "The Silent Road")

    def test_unauthorized_user_cannot_create_movie(self):
        payload = {
            "title": "Hidden Truth",
            "description": "An exploration of mystery and truth",
            "duration": 140,
            "genres": [self.genre2.id],
            "actors": [self.actor1.id, self.actor2.id],
        }
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_non_admin_user_cannot_create_movie(self):
        self.client.force_authenticate(user=self.regular_user)
        payload = {
            "title": "Shattered Memories",
            "description": "A journey through broken memories",
            "duration": 125,
            "genres": [self.genre2.id],
            "actors": [self.actor1.id, self.actor2.id],
        }
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_empty_movies_list(self):
        Movie.objects.all().delete()
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)
