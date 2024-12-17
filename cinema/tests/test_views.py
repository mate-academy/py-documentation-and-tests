import tempfile

from PIL import Image
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from cinema.models import Movie, Genre, Actor


MOVIE_LIST_URL = reverse("cinema:movie-list")


class MovieViewSetTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin_user = get_user_model().objects.create_superuser(
            email="admin@example.com", password="adminpass"
        )
        cls.regular_user = get_user_model().objects.create_user(
            email="user@example.com", password="userpass"
        )
        cls.genre = Genre.objects.create(name="Action")
        cls.actor = Actor.objects.create(first_name="John", last_name="Green")
        cls.movie = Movie.objects.create(
            title="Test Movie", description="Test", duration=120
        )
        cls.movie.genres.add(cls.genre)
        cls.movie.actors.add(cls.actor)

    def setUp(self):
        """Authenticate user before every test"""
        refresh = RefreshToken.for_user(self.admin_user)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}"
        )

    def test_list_movies_unauthorized(self):
        """Test creating a movie without authentication."""
        self.client.force_authenticate(user=None)
        response = self.client.get(MOVIE_LIST_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_movie_detail_unauthorized(self):
        """Test retrieving a movie's detail without authentication."""
        self.client.force_authenticate(user=None)
        response = self.client.get(
            reverse("cinema:movie-detail", args=(self.movie.id,))
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_movies(self):
        """Test retrieving the list of movies."""
        response = self.client.get(MOVIE_LIST_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Test Movie", str(response.data))

    def test_filter_movies_by_title(self):
        """Test filtering movies by title."""
        response = self.client.get(MOVIE_LIST_URL, {"title": "Test"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Test Movie", str(response.data))

    def test_filter_movies_by_genres(self):
        """Test filtering movies by genres."""
        response = self.client.get(MOVIE_LIST_URL, {"genres": self.genre.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Test Movie", str(response.data))

    def test_filter_movies_by_actors(self):
        """Test filtering movies by actors."""
        response = self.client.get(MOVIE_LIST_URL, {"actors": self.actor.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Test Movie", str(response.data))

    def test_retrieve_movie_detail(self):
        """Test retrieving a movie's detail."""
        response = self.client.get(
            reverse("cinema:movie-detail", args=(self.movie.id,))
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], self.movie.title)

    def test_create_movie_as_admin(self):
        """Test creating a movie as an admin user."""
        payload = {
            "title": "New Movie",
            "description": "New Description",
            "duration": 100,
            "genres": [self.genre.id],
            "actors": [self.actor.id],
        }
        response = self.client.post(MOVIE_LIST_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_movie_as_regular_user(self):
        """Test regular user cannot create a movie."""
        refresh = RefreshToken.for_user(self.regular_user)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}"
        )
        payload = {
            "title": "New Movie",
            "description": "New Description",
            "duration": 100,
            "genres": [self.genre.id],
            "actors": [self.actor.id],
        }
        response = self.client.post(MOVIE_LIST_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_upload_image_as_admin(self):
        """Test uploading an image as an admin user."""
        url = reverse("cinema:movie-upload-image", args=[self.movie.id])
        with tempfile.NamedTemporaryFile(suffix=".jpg") as temp_file:
            img = Image.new("RGB", (10, 10))
            img.save(temp_file, format="JPEG")
            temp_file.seek(0)
            response = self.client.post(
                url, {"image": temp_file}, format="multipart"
            )
        self.assertIn("image", response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_upload_image_as_regular_user(self):
        """Test regular user cannot upload an image."""
        refresh = RefreshToken.for_user(self.regular_user)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}"
        )
        url = reverse("cinema:movie-upload-image", args=[self.movie.id])
        response = self.client.post(url, {"image": "dummy_image"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
