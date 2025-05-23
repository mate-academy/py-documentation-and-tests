import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor
from cinema.serializers import MovieSerializer

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


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


class MovieViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            email="test@gmail.com",
            password="testpassword",
        )
        tokens = get_tokens_for_user(self.user)
        self.access_token = tokens['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')

        self.genre1 = Genre.objects.create(name="Action")
        self.actor = Actor.objects.create(first_name="Tom", last_name="Hanks")
        self.movie1 = Movie.objects.create(
            title="Test Movie",
            description="Test Movie Description",
            duration=90
        )
        self.movie1.genres.add(self.genre1)
        self.movie = Movie.objects.create(
            title="Saving Private Ryan",
            description="Saving Private Ryan Description",
            duration=90
        )
        self.movie.actors.add(self.actor)

    def test_filter_by_title(self):
        response = self.client.get(reverse("cinema:movie-list"), {"title": "Avengers"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_filter_by_genres(self):
        response = self.client.get(reverse("cinema:movie-list"), {"genres": "1"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = [movie["title"] for movie in response.data["results"]]
        self.assertIn(self.movie1.title, titles)

    def test_filter_by_actors(self):
        url = reverse("cinema:movie-list")
        res = self.client.get(url, {"actors": str(self.actor.id)})
        self.assertEqual(res.status_code, 200)
        data = res.data["results"] if "results" in res.data else res.data
        titles = [movie["title"] for movie in data]
        self.assertIn(self.movie.title, titles)

    def test_authenticated_access(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        url = reverse("cinema:movie-list")
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)


class UnauthenticatedMovieViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_unauthenticated_movie_view(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

class AuthenticatedMovieViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            email="test@gmail.com",
            password="testpassword"
        )
        self.client.force_authenticate(self.user)

    def sample_movie(self, **params):
        defaults = {
            "title": "Test Movie",
            "description": "Test Movie Description",
            "duration": 90,
        }
        defaults.update(params)
        return Movie.objects.create(**defaults)


class MovieRetrieveTests(TestCase):
    def test_retrieve_movie(self):
        movie = sample_movie()
        url = reverse("cinema:movie-detail", args=[movie.id])

        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], movie.id)
        self.assertEqual(res.data["title"], movie.title)

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="testuser@gmail.com",
            password="testpass123"
        )
        self.client.force_authenticate(user=self.user)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Test Movie Title",
            "description": "Test Movie Description",
            "duration": 90,
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            email="test@gmail.com",
            password="testpassword",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)

    def test_create_movie_admin(self):
        admin = get_user_model().objects.create_superuser(
            email="admin@gmail.com",
            password="adminpass123"
        )
        self.client.force_authenticate(user=admin)

        genre = Genre.objects.create(name="Action")
        actor = Actor.objects.create(first_name="Tom", last_name="Hanks")

        payload = {
            "title": "Some Movie",
            "description": "Some Description",
            "duration": 120,
            "genres": [genre.id],
            "actors": [actor.id]
        }

        res = self.client.post(reverse("cinema:movie-list"), payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn("id", res.data)

    def test_delete_movie_not_allowed(self):
        movie = sample_movie()
        url = reverse("cinema:movie-detail", args=[movie.id])
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_upload_movie_image(self):
        movie = sample_movie()
        url = reverse("cinema:movie-upload-image", args=[movie.id])

        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (100, 100))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(MOVIE_SESSION_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

class MovieSerializerTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="testuser@example.com",
            password="testpass123"
        )
        self.client.force_authenticate(self.user)

        self.movie = Movie.objects.create(
            title="Test Movie",
            description="Test Desc",
            duration=120,
        )

    def test_movie_serializer(self):
        serializer = MovieSerializer(self.movie)
        data = serializer.data

        self.assertEqual(data["title"], self.movie.title)
        self.assertEqual(data["description"], self.movie.description)
        self.assertEqual(data["duration"], self.movie.duration)
