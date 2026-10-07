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


class MovieApiTests(TestCase):
    """Tests for every standard MovieViewSet action and its filters."""

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="member@cinema.com",
            password="testpass123",
        )
        self.admin = get_user_model().objects.create_superuser(
            email="admin@cinema.com",
            password="testpass123",
        )

    def test_list_movies_requires_authentication(self):
        response = self.client.get(MOVIE_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_movies_for_authenticated_user(self):
        movie = sample_movie(title="A movie")
        self.client.force_authenticate(self.user)

        response = self.client.get(MOVIE_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["title"], movie.title)
        self.assertIn("genres", response.data[0])

    def test_retrieve_movie_returns_detail_serializer(self):
        movie = sample_movie()
        genre = sample_genre()
        actor = sample_actor()
        movie.genres.add(genre)
        movie.actors.add(actor)
        self.client.force_authenticate(self.user)

        response = self.client.get(detail_url(movie.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["genres"][0]["name"], genre.name)
        self.assertEqual(response.data["actors"][0]["full_name"], actor.full_name)

    def test_filter_movies_by_title(self):
        first_movie = sample_movie(title="Vacation story")
        sample_movie(title="Winter tale")
        self.client.force_authenticate(self.user)

        response = self.client.get(MOVIE_URL, {"title": "vacation"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([movie["id"] for movie in response.data], [first_movie.id])

    def test_filter_movies_by_genres(self):
        genre = sample_genre(name="Comedy")
        matching_movie = sample_movie(title="Comedy film")
        matching_movie.genres.add(genre)
        sample_movie(title="Drama film")
        self.client.force_authenticate(self.user)

        response = self.client.get(MOVIE_URL, {"genres": str(genre.id)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([movie["id"] for movie in response.data], [matching_movie.id])

    def test_filter_movies_by_actors(self):
        actor = sample_actor(first_name="Tom", last_name="Hardy")
        matching_movie = sample_movie(title="Actor film")
        matching_movie.actors.add(actor)
        sample_movie(title="Other film")
        self.client.force_authenticate(self.user)

        response = self.client.get(MOVIE_URL, {"actors": str(actor.id)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([movie["id"] for movie in response.data], [matching_movie.id])

    def test_create_movie_is_forbidden_for_regular_user(self):
        self.client.force_authenticate(self.user)

        response = self.client.post(
            MOVIE_URL,
            {"title": "New movie", "description": "Description", "duration": 100},
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_movie_for_admin(self):
        genre = sample_genre()
        actor = sample_actor()
        self.client.force_authenticate(self.admin)

        response = self.client.post(
            MOVIE_URL,
            {
                "title": "New movie",
                "description": "Description",
                "duration": 100,
                "genres": [genre.id],
                "actors": [actor.id],
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Movie.objects.filter(title="New movie").exists())

    def test_jwt_authentication_can_access_movie_list(self):
        token_url = reverse("user:token-obtain-pair")
        token_response = self.client.post(
            token_url,
            {"email": self.user.email, "password": "testpass123"},
        )
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {token_response.data['access']}"
        )

        response = self.client.get(MOVIE_URL)

        self.assertEqual(token_response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
