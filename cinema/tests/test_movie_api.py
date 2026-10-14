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
    """Return URL for movie image upload"""
    return reverse("cinema:movie-upload-image", args=[movie_id])


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


class UnauthenticatedMovieApiTests(TestCase):
    """MovieViewSet must not be available for anonymous users."""

    def setUp(self):
        cache.clear()
        self.client = APIClient()

    def test_list_requires_auth(self):
        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_detail_requires_auth(self):
        movie = sample_movie()
        res = self.client.get(detail_url(movie.id))

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_requires_auth(self):
        payload = {
            "title": "Title",
            "description": "Description",
            "duration": 90,
            "genres": [],
            "actors": [],
        }
        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    """A regular (non-staff) user may only read movies."""

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user@cinema.com", password="testpass123"
        )
        self.client.force_authenticate(self.user)

    def test_list_movies(self):
        sample_movie(title="First movie")
        sample_movie(title="Second movie")

        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)
        self.assertIn("genres", res.data[0])
        self.assertIn("actors", res.data[0])
        self.assertIn("image", res.data[0])

    def test_retrieve_movie_detail(self):
        genre = sample_genre(name="Action")
        actor = sample_actor()
        movie = sample_movie(title="Inception")
        movie.genres.add(genre)
        movie.actors.add(actor)

        res = self.client.get(detail_url(movie.id))

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["title"], "Inception")
        self.assertEqual(res.data["genres"][0]["name"], "Action")
        self.assertEqual(
            res.data["actors"][0]["full_name"], "George Clooney"
        )

    def test_create_movie_forbidden_for_non_admin(self):
        payload = {
            "title": "New movie",
            "description": "Description",
            "duration": 100,
            "genres": [],
            "actors": [],
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Movie.objects.filter(title="New movie").exists())

    def test_filter_movies_by_title(self):
        sample_movie(title="The Departed")
        sample_movie(title="Inception")

        res = self.client.get(MOVIE_URL, {"title": "Departed"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], "The Departed")

    def test_filter_movies_by_genres(self):
        action = sample_genre(name="Action")
        drama = sample_genre(name="Drama")
        movie_action = sample_movie(title="Action movie")
        movie_drama = sample_movie(title="Drama movie")
        movie_action.genres.add(action)
        movie_drama.genres.add(drama)

        res = self.client.get(MOVIE_URL, {"genres": f"{action.id}"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        titles = [movie["title"] for movie in res.data]
        self.assertIn("Action movie", titles)
        self.assertNotIn("Drama movie", titles)

    def test_filter_movies_by_actors(self):
        actor_one = sample_actor(first_name="Leonardo", last_name="DiCaprio")
        actor_two = sample_actor(first_name="Matt", last_name="Damon")
        movie_one = sample_movie(title="First")
        movie_two = sample_movie(title="Second")
        movie_one.actors.add(actor_one)
        movie_two.actors.add(actor_two)

        res = self.client.get(MOVIE_URL, {"actors": f"{actor_one.id}"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        titles = [movie["title"] for movie in res.data]
        self.assertIn("First", titles)
        self.assertNotIn("Second", titles)

    def test_upload_image_forbidden_for_non_admin(self):
        movie = sample_movie()
        url = image_upload_url(movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(url, {"image": ntf}, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTests(TestCase):
    """A staff user has full access to MovieViewSet."""

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.admin = get_user_model().objects.create_superuser(
            email="admin@cinema.com", password="adminpass123"
        )
        self.client.force_authenticate(self.admin)

    def test_create_movie(self):
        genre = sample_genre(name="Sci-Fi")
        actor = sample_actor(first_name="Elliot", last_name="Page")
        payload = {
            "title": "New movie",
            "description": "Great description",
            "duration": 120,
            "genres": [genre.id],
            "actors": [actor.id],
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(id=res.data["id"])
        self.assertEqual(movie.title, "New movie")
        self.assertEqual(list(movie.genres.all()), [genre])
        self.assertEqual(list(movie.actors.all()), [actor])

    def test_create_movie_invalid_data(self):
        payload = {"description": "Missing required fields"}

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_non_existing_movie_returns_404(self):
        res = self.client.get(detail_url(9999))

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)


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


class JWTAuthenticationTests(TestCase):
    """Verify that JWT tokens issued by the API authenticate requests."""

    def setUp(self):
        cache.clear()
        self.client = APIClient()

    def test_obtain_token_and_access_movies(self):
        get_user_model().objects.create_user(
            email="jwt.user@cinema.com", password="testpass123"
        )

        token_res = self.client.post(
            reverse("user:token_obtain_pair"),
            {"email": "jwt.user@cinema.com", "password": "testpass123"},
        )

        self.assertEqual(token_res.status_code, status.HTTP_200_OK)
        self.assertIn("access", token_res.data)

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {token_res.data['access']}"
        )
        movies_res = self.client.get(MOVIE_URL)

        self.assertEqual(movies_res.status_code, status.HTTP_200_OK)

    def test_obtain_token_with_wrong_credentials(self):
        res = self.client.post(
            reverse("user:token_obtain_pair"),
            {"email": "wrong@cinema.com", "password": "wrongpass"},
        )

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
