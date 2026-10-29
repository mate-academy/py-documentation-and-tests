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


class MovieViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "viewer@example.com", password="password"
        )
        self.admin = get_user_model().objects.create_superuser(
            "admin@example.com", "password"
        )
        self.genre = sample_genre()
        self.actor = sample_actor()
        self.movie = sample_movie(title="The Sample")
        self.movie.genres.add(self.genre)
        self.movie.actors.add(self.actor)

    def test_list_requires_authentication(self):
        response = self.client.get(MOVIE_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_user_can_list_movies(self):
        self.client.force_authenticate(self.user)

        response = self.client.get(MOVIE_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], self.movie.title)

    def test_list_filters_by_title_genre_and_actor(self):
        self.client.force_authenticate(self.user)
        other = sample_movie(title="Another film")
        other.genres.add(self.genre)
        other_actor = sample_actor(first_name="Different")
        other.actors.add(other_actor)

        title_response = self.client.get(MOVIE_URL, {"title": "sample"})
        genre_response = self.client.get(
            MOVIE_URL, {"genres": str(self.genre.id)}
        )
        actor_response = self.client.get(
            MOVIE_URL, {"actors": str(self.actor.id)}
        )

        self.assertEqual(
            [item["id"] for item in title_response.data], [self.movie.id]
        )
        self.assertEqual(len(genre_response.data), 2)
        self.assertEqual(
            [item["id"] for item in actor_response.data], [self.movie.id]
        )

    def test_admin_can_create_movie_and_regular_user_cannot(self):
        payload = {
            "title": "New movie",
            "description": "A description",
            "duration": 100,
            "genres": [self.genre.id],
            "actors": [self.actor.id],
        }
        self.client.force_authenticate(self.user)
        denied = self.client.post(MOVIE_URL, payload, format="json")
        self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(self.admin)
        created = self.client.post(MOVIE_URL, payload, format="json")

        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self.assertEqual(created.data["title"], "New movie")

    def test_retrieve_returns_nested_genres_and_actors(self):
        self.client.force_authenticate(self.user)

        response = self.client.get(detail_url(self.movie.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["genres"][0]["name"], self.genre.name)
        self.assertEqual(
            response.data["actors"][0]["full_name"], self.actor.full_name
        )

    def test_unknown_movie_returns_not_found(self):
        self.client.force_authenticate(self.user)

        response = self.client.get(detail_url(99999))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
