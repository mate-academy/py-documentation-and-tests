import tempfile
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from cinema.models import Movie, Genre, Actor
from PIL import Image
from functools import wraps


def upload_test(user_type, expected_status_code):

    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if user_type == "admin":
                self.client.force_authenticate(user=self.admin_user)
            elif user_type == "user":
                self.client.force_authenticate(user=self.user)
            else:
                raise ValueError("Invalid user type. Use 'admin' or 'user'.")

            with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
                img = Image.new("RGB", (10, 10))
                img.save(ntf, format="JPEG")
                ntf.seek(0)

                response = self.client.post(
                    f"/api/cinema/movies/{self.movie.id}/upload-image/",
                    {"image": ntf},
                    format="multipart",
                )

            self.assertEqual(response.status_code, expected_status_code)

            if user_type == "admin" and expected_status_code == status.HTTP_200_OK:
                self.movie.refresh_from_db()
                self.assertTrue(bool(self.movie.image))

            return func(self, *args, **kwargs)

        return wrapper

    return decorator


class MovieViewSetTests(TestCase):
    """Tests to verify the functionality of the movie-related API"""

    def setUp(self):
        self.client = APIClient()
        self.admin_user = get_user_model().objects.create_superuser(
            email="admin@admin.com", password="adminpass", is_staff=True
        )
        self.user = get_user_model().objects.create_user(
            email="user@user.com", password="userpass"
        )

        self.genre = Genre.objects.create(name="Action")
        self.actor = Actor.objects.create(first_name="John", last_name="Doe")
        self.movie = Movie.objects.create(
            title="Test Movie", description="Test Description", duration=120
        )
        self.movie.genres.add(self.genre)
        self.movie.actors.add(self.actor)

        self.client.force_authenticate(user=self.user)

    def test_list_movies(self):
        """Test retrieving the list of movies with optional filters"""
        response = self.client.get("/api/cinema/movies/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Test Movie")

    def test_retrieve_movie(self):
        """Test retrieving a single movie by ID"""
        response = self.client.get(f"/api/cinema/movies/{self.movie.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "Test Movie")
        self.assertIn("genres", response.data)
        self.assertIn("actors", response.data)

    def test_filter_movies_by_title(self):
        """Test filtering movies by title"""
        response = self.client.get("/api/cinema/movies/", {"title": "Test"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Test Movie")

    def test_filter_movies_by_genres(self):
        """Test filtering movies by genres"""
        response = self.client.get("/api/cinema/movies/", {"genres": self.genre.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Test Movie")

    def test_filter_movies_by_actors(self):
        """Test filtering movies by actors"""
        response = self.client.get("/api/cinema/movies/", {"actors": self.actor.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Test Movie")


class MovieUploadTests(TestCase):
    """Tests to verify the functionality of uploading images to the server"""

    def setUp(self):
        self.client = APIClient()
        self.admin_user = get_user_model().objects.create_superuser(
            email="admin@admin.com", password="adminpass"
        )
        self.user = get_user_model().objects.create_user(
            email="user@user.com", password="userpass"
        )

        self.movie = Movie.objects.create(
            title="Test Movie", description="Test Description", duration=120
        )

    @upload_test(user_type="admin", expected_status_code=status.HTTP_200_OK)
    def test_upload_image_as_admin(self):
        """Test uploading an image to a movie as an admin"""
        pass

    @upload_test(user_type="user", expected_status_code=status.HTTP_403_FORBIDDEN)
    def test_upload_image_non_admin(self):
        """Test uploading an image for a movie as a regular user"""
        pass
