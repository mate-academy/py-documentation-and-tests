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
        "show_time": "2022-06-02T14:00:00Z",
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


class PublicMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_authentication_is_required(self):
        response = self.client.get(MOVIE_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class MovieViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user@example.com",
            password="testpass123",
        )
        self.client.force_authenticate(self.user)

        self.genre_drama = sample_genre(name="Drama")
        self.genre_comedy = sample_genre(name="Comedy")
        self.actor_one = sample_actor(
            first_name="George",
            last_name="Clooney",
        )
        self.actor_two = sample_actor(
            first_name="Emma",
            last_name="Stone",
        )

        self.movie_one = sample_movie(title="Ocean Eleven")
        self.movie_one.genres.add(self.genre_drama)
        self.movie_one.actors.add(self.actor_one)

        self.movie_two = sample_movie(title="Easy A")
        self.movie_two.genres.add(self.genre_comedy)
        self.movie_two.actors.add(self.actor_two)

    def test_list_movies(self):
        response = self.client.get(MOVIE_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_retrieve_movie_detail(self):
        response = self.client.get(detail_url(self.movie_one.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], self.movie_one.title)
        self.assertEqual(response.data["genres"][0]["name"], "Drama")
        self.assertEqual(response.data["actors"][0]["full_name"],
                         "George Clooney")

    def test_filter_movies_by_title(self):
        response = self.client.get(MOVIE_URL, {"title": "ocean"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([movie["id"] for movie in response.data],
                         [self.movie_one.id])

    def test_filter_movies_by_genres(self):
        response = self.client.get(
            MOVIE_URL,
            {"genres": str(self.genre_comedy.id)},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([movie["id"] for movie in response.data],
                         [self.movie_two.id])

    def test_filter_movies_by_actors(self):
        response = self.client.get(
            MOVIE_URL,
            {"actors": str(self.actor_one.id)},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([movie["id"] for movie in response.data],
                         [self.movie_one.id])

    def test_regular_user_cannot_create_movie(self):
        response = self.client.post(
            MOVIE_URL,
            {
                "title": "New movie",
                "description": "Description",
                "duration": 100,
                "genres": [self.genre_drama.id],
                "actors": [self.actor_one.id],
            },
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_create_movie(self):
        admin = get_user_model().objects.create_superuser(
            email="admin@example.com",
            password="testpass123",
        )
        self.client.force_authenticate(admin)
        payload = {
            "title": "New movie",
            "description": "Description",
            "duration": 100,
            "genres": [self.genre_drama.id],
            "actors": [self.actor_one.id],
        }

        response = self.client.post(MOVIE_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(id=response.data["id"])
        self.assertEqual(movie.title, payload["title"])
        self.assertEqual(list(movie.genres.all()), [self.genre_drama])
        self.assertEqual(list(movie.actors.all()), [self.actor_one])


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
