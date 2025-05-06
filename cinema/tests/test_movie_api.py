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


class MovieFiltersTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "user@test.com", "testpass123"
        )
        self.client.force_authenticate(self.user)

        self.genre1 = sample_genre(name="Comedy")
        self.genre2 = sample_genre(name="Action")

        self.actor1 = sample_actor(first_name="Tom", last_name="Hanks")
        self.actor2 = sample_actor(
            first_name="Scarlett", last_name="Johansson"
        )

        self.movie1 = sample_movie(title="Funny Movie")
        self.movie1.genres.add(self.genre1)
        self.movie1.actors.add(self.actor1)

        self.movie2 = sample_movie(title="Action Movie")
        self.movie2.genres.add(self.genre2)
        self.movie2.actors.add(self.actor2)

        self.movie3 = sample_movie(title="Funny Action Movie")
        self.movie3.genres.add(self.genre1, self.genre2)
        self.movie3.actors.add(self.actor1, self.actor2)

    def test_filter_by_title(self):
        res = self.client.get(MOVIE_URL, {"title": "funny"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        titles = [movie["title"] for movie in res.data]
        self.assertIn(self.movie1.title, titles)
        self.assertIn(self.movie3.title, titles)
        self.assertNotIn(self.movie2.title, titles)

    def test_filter_by_genres(self):
        res = self.client.get(MOVIE_URL, {"genres": f"{self.genre1.id}"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ids = [movie["id"] for movie in res.data]
        self.assertIn(self.movie1.id, ids)
        self.assertIn(self.movie3.id, ids)
        self.assertNotIn(self.movie2.id, ids)

    def test_filter_by_actors(self):
        res = self.client.get(MOVIE_URL, {"actors": f"{self.actor2.id}"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ids = [movie["id"] for movie in res.data]
        self.assertIn(self.movie2.id, ids)
        self.assertIn(self.movie3.id, ids)
        self.assertNotIn(self.movie1.id, ids)

    def test_filter_by_multiple_criteria(self):
        res = self.client.get(
            MOVIE_URL,
            {
                "title": "action",
                "genres": f"{self.genre2.id}",
                "actors": f"{self.actor2.id}",
            },
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ids = [movie["id"] for movie in res.data]
        self.assertIn(self.movie2.id, ids)
        self.assertIn(self.movie3.id, ids)
        self.assertNotIn(self.movie1.id, ids)
