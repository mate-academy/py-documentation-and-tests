import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient, APITestCase
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")
MOVIE_SESSION_URL = reverse("cinema:moviesession-list")


class MovieViewSetTests(APITestCase):
    def setUp(self):
        self.client = APIClient()

    def test_list_movies_unauthorized(self):
        response = self.client.get(MOVIE_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class MovieViewSetAuthorizedTests(APITestCase):
    def setUp(self):
        self.auth_user = get_user_model().objects.create_user(
            email="authuser@auth.com", password="authpass"
        )
        self.client.force_authenticate(self.auth_user)

        genre_drama = Genre.objects.create(name="Drama")
        genre_action = Genre.objects.create(name="Action")
        actor_john_doe = Actor.objects.create(first_name="John", last_name="Doe")
        actor_jane_doe = Actor.objects.create(first_name="Jane", last_name="Doe")

        self.movie1 = Movie.objects.create(
            title="Test Drama Movie", description="Drama movie", duration=120
        )
        self.movie1.genres.set([genre_drama])
        self.movie1.actors.set([actor_john_doe])

        self.movie2 = Movie.objects.create(
            title="Test Action Movie", description="Action movie", duration=150
        )
        self.movie2.genres.set([genre_action])
        self.movie2.actors.set([actor_jane_doe])

        self.movie_url = reverse("cinema:movie-detail", args=[self.movie1.id])

    def test_list_movies_by_title(self):
        response = self.client.get(reverse("cinema:movie-list"), {"title": "Drama"})

        serializer1 = MovieListSerializer(self.movie1)
        serializer2 = MovieListSerializer(self.movie2)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertIn(serializer1.data, response.data)
        self.assertNotIn(serializer2.data, response.data)

    def test_list_movies_by_genres(self):
        response = self.client.get(
            reverse("cinema:movie-list"), {"genres": f"{self.movie1.genres.first().id}"}
        )

        serializer1 = MovieListSerializer(self.movie1)
        serializer2 = MovieListSerializer(self.movie2)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertIn(serializer1.data, response.data)
        self.assertNotIn(serializer2.data, response.data)

    def test_list_movies_by_actors(self):
        response = self.client.get(
            reverse("cinema:movie-list"), {"actors": f"{self.movie1.actors.first().id}"}
        )

        serializer1 = MovieListSerializer(self.movie1)
        serializer2 = MovieListSerializer(self.movie2)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertIn(serializer1.data, response.data)
        self.assertNotIn(serializer2.data, response.data)

    def test_retrieve_movie_authorized(self):
        response = self.client.get(self.movie_url)

        serializer = MovieDetailSerializer(self.movie1)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(serializer.data, response.data)


class MovieViewSetAdminTests(APITestCase):
    def setUp(self):
        self.admin_user = get_user_model().objects.create_user(
            email="adminuser@admin.com", password="adminpass", is_staff=True
        )
        self.client.force_authenticate(self.admin_user)

        self.movie = Movie.objects.create(title="Test Movie", duration=120)
        self.movie_url = reverse("cinema:movie-detail", args=[self.movie.id])

    def test_list_movies_admin(self):
        response = self.client.get(reverse("cinema:movie-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_movie_admin(self):
        response = self.client.get(self.movie_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_movie_admin(self):
        genre_action = Genre.objects.create(name="Action")
        actor_john_doe = Actor.objects.create(first_name="John", last_name="Doe")
        payload = {
            "title": "New Test Movie",
            "description": "Description for the new movie",
            "duration": 120,
            "genres": [genre_action.id],
            "actors": [actor_john_doe.id],
        }

        response = self.client.post(reverse("cinema:movie-list"), payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


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
    cinema_hall = CinemaHall.objects.create(name="Blue", rows=20, seats_in_row=20)

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
