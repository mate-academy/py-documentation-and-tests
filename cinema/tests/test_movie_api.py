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


def sample_movie(**params):
    defaults = {
        "title": "Sample movie",
        "description": "Sample description",
        "duration": 90,
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)


def sample_genre(**params):
    defaults = {"name": "Drama"}
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
    return reverse("cinema:movie-upload-image", args=[movie_id])


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


class MovieImageUploadTests(TestCase):
    def setUp(self):
        self.client: APIClient = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)
        self.movie = sample_movie()
        self.genre = sample_genre()
        self.actor = sample_actor()
        self.movie_session = sample_movie_session(movie=self.movie)

    def tearDown(self):
        if self.movie.image:
            if os.path.exists(self.movie.image.path):
                self.movie.image.delete()

    def test_upload_image_to_movie(self):
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


class MovieViewSetTests(TestCase):
    def setUp(self):
        self.client: APIClient = APIClient()
        self.user = get_user_model().objects.create_user(
            "user@test.com", "password123"
        )
        self.admin = get_user_model().objects.create_superuser(
            "admin@test.com", "admin123"
        )
        self.client.force_authenticate(self.user)

        self.genre = sample_genre()
        self.actor = sample_actor()
        self.movie = sample_movie()
        self.movie.genres.add(self.genre)
        self.movie.actors.add(self.actor)

    def test_list_movies(self):
        res = self.client.get(MOVIE_URL)
        data = res.data.get("results") if isinstance(res.data, dict) else res.data

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["title"], self.movie.title)

    def test_filter_movies_by_title(self):
        sample_movie(title="Another movie")
        res = self.client.get(MOVIE_URL, {"title": "Sample"})
        data = res.data.get("results") if isinstance(res.data, dict) else res.data

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["title"], self.movie.title)

    def test_filter_movies_by_genres(self):
        genre2 = sample_genre(name="Comedy")
        movie2 = sample_movie(title="Comedy Movie")
        movie2.genres.add(genre2)
        res = self.client.get(MOVIE_URL, {"genres": f"{self.genre.id}"})
        data = res.data.get("results") if isinstance(res.data, dict) else res.data

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["title"], self.movie.title)

    def test_filter_movies_by_actors(self):
        actor2 = sample_actor(first_name="Brad", last_name="Pitt")
        movie2 = sample_movie(title="Brad Movie")
        movie2.actors.add(actor2)
        res = self.client.get(MOVIE_URL, {"actors": f"{self.actor.id}"})
        data = res.data.get("results") if isinstance(res.data, dict) else res.data

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["title"], self.movie.title)

    def test_retrieve_movie_detail(self):
        url = detail_url(self.movie.id)
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["title"], self.movie.title)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "New Movie",
            "description": "Description",
            "duration": 120,
            "genres": [self.genre.id],
            "actors": [self.actor.id],
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_movie_admin_allowed(self):
        self.client.force_authenticate(self.admin)
        payload = {
            "title": "Admin Movie",
            "description": "Description",
            "duration": 120,
            "genres": [self.genre.id],
            "actors": [self.actor.id],
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_update_movie_admin_allowed(self):
        self.client.force_authenticate(self.admin)
        url = detail_url(self.movie.id)
        res = self.client.patch(url, {"title": "Updated Title"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.movie.refresh_from_db()
        self.assertEqual(self.movie.title, "Updated Title")

    def test_delete_movie_admin_allowed(self):
        self.client.force_authenticate(self.admin)
        url = detail_url(self.movie.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Movie.objects.filter(id=self.movie.id).exists())
