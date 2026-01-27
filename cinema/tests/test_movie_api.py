import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient, APITestCase
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


class AuthenticatedMovieTests(APITestCase):
    def setUp(self):
        self.user_payload = {
            "email": "test.user@cinema.com",
            "password": "UserTest",
        }

        self.user = get_user_model().objects.create_user(
            email=self.user_payload["email"],
            password=self.user_payload["password"],
        )

        token_url = reverse("user:token_obtain_pair")

        response = self.client.post(token_url, self.user_payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.token = response.data["access"]

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.token}"
        )

    def test_list_movies(self):
        sample_movie()
        sample_movie(title="Avatar")

        response = self.client.get(MOVIE_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_retrieve_movie(self):
        movie = sample_movie()

        url = reverse("cinema:movie-detail", args=[movie.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], movie.title)

    def test_create_movie_not_allowed(self):
        payload = {
            "title": "Avatar",
            "description": "Description",
            "duration": 90,
        }

        response = self.client.post(MOVIE_URL, payload)

        self.assertIn(
            response.status_code,
            [
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
                status.HTTP_405_METHOD_NOT_ALLOWED,
            ]
        )

    def test_update_movie(self):
        movie = sample_movie()

        url = reverse("cinema:movie-detail", args=[movie.id])

        payload = {
            "title": "Updated Title",
            "description": movie.description,
            "duration": movie.duration,
        }

        response = self.client.put(url, payload)

        self.assertIn(
            response.status_code,
            [
                status.HTTP_403_FORBIDDEN,
            ]
        )

    def test_partial_update_movie(self):
        movie = sample_movie()

        url = reverse("cinema:movie-detail", args=[movie.id])
        response = self.client.patch(url, {"title": "Updated Title"})

        self.assertIn(
            response.status_code,
            [
                status.HTTP_403_FORBIDDEN,
            ]
        )

    def test_delete_movie(self):
        movie = sample_movie()

        url = reverse("cinema:movie-detail", args=[movie.id])
        response = self.client.delete(url)

        self.assertIn(
            response.status_code,
            [
                status.HTTP_403_FORBIDDEN,
            ]
        )


class UnauthenticatedMovieTests(APITestCase):
    def test_list_unauthenticated_users(self):
        sample_movie()
        sample_movie(title="Avatar")

        response = self.client.get(MOVIE_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class MovieFilterTests(APITestCase):
    def setUp(self):
        self.user_payload = {
            "email": "test.user@cinema.com",
            "password": "UserTest",
        }

        self.user = get_user_model().objects.create_user(
            email=self.user_payload["email"],
            password=self.user_payload["password"],
        )

        token_url = reverse("user:token_obtain_pair")

        response = self.client.post(token_url, self.user_payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.token = response.data["access"]

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.token}"
        )

    def test_filter_by_title(self):
        sample_movie()
        sample_movie(title="Avatar")

        response = self.client.get(MOVIE_URL, {"title": "Avatar"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_filter_by_genres(self):
        action = sample_genre(name="Action")
        drama = sample_genre(name="Drama")

        movie1 = sample_movie(title="Movie 1")
        movie1.genres.set([action])

        movie2 = sample_movie(title="Movie 2")
        movie2.genres.set([drama])

        response = self.client.get(MOVIE_URL, {"genres": action.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_filter_by_actors(self):
        keanu = sample_actor(first_name="Keanu", last_name="Reeves")
        tom = sample_actor(first_name="Tom", last_name="Cruise")

        movie1 = sample_movie(title="Movie 1")
        movie1.actors.set([keanu])

        movie2 = sample_movie(title="Movie 2")
        movie2.actors.set([tom])

        response = self.client.get(MOVIE_URL, {"actors": tom.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
