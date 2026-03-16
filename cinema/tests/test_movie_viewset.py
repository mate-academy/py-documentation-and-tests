from django.urls import reverse
from rest_framework.test import APIClient, APITestCase
from rest_framework import status
from cinema.models import Movie, Genre, Actor
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
import io

MOVIE_URL = reverse("cinema:movie-list")


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


def upload_image_url(movie_id):
    return reverse("cinema:movie-upload-image", args=[movie_id])


def generate_image_file():
    file = io.BytesIO()
    image = Image.new("RGB", (10, 10), color="red")
    image.save(file, "JPEG")
    file.seek(0)
    return SimpleUploadedFile("test.jpg", file.read(), content_type="image/jpeg")


class MovieViewSetTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        # створюємо користувачів у тестовій базі
        self.user = get_user_model().objects.create_user(
            email="test@cinema.com", password="testpass"
        )
        self.admin = get_user_model().objects.create_superuser(
            email="admin@cinema.com", password="AdminPass123"
        )
        # тестові дані
        self.genre = Genre.objects.create(name="Action")
        self.actor = Actor.objects.create(first_name="John", last_name="Doe")
        self.movie = Movie.objects.create(
            title="Test Movie", description="Desc", duration=120
        )
        self.movie.genres.add(self.genre)
        self.movie.actors.add(self.actor)

    def authenticate(self, email, password):
        """Helper to get JWT token and set credentials"""
        res = self.client.post("/api/token/", {"email": email, "password": password})
        self.assertEqual(res.status_code, 200, msg=res.data)  # покаже detail, якщо токен не видали
        token = res.data.get("access")
        self.assertIsNotNone(token, msg=res.data)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + token)

    def test_list_movies_requires_auth(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

        self.authenticate("test@cinema.com", "testpass")
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)

    def test_filter_movies_by_title(self):
        self.authenticate("test@cinema.com", "testpass")
        res = self.client.get(MOVIE_URL, {"title": "Test"})
        self.assertEqual(len(res.data), 1)

    def test_filter_movies_by_genre(self):
        self.authenticate("test@cinema.com", "testpass")
        res = self.client.get(MOVIE_URL, {"genres": str(self.genre.id)})
        self.assertEqual(len(res.data), 1)

    def test_filter_movies_by_actor(self):
        self.authenticate("test@cinema.com", "testpass")
        res = self.client.get(MOVIE_URL, {"actors": str(self.actor.id)})
        self.assertEqual(len(res.data), 1)

    def test_retrieve_movie_detail_requires_auth(self):
        url = detail_url(self.movie.id)
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

        self.authenticate("test@cinema.com", "testpass")
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["title"], self.movie.title)

    def test_create_movie_admin_only(self):
        payload = {
            "title": "New Movie",
            "description": "Desc",
            "duration": 90,
            "genres": [self.genre.id],
            "actors": [self.actor.id],
        }
        self.authenticate("test@cinema.com", "testpass")
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        self.authenticate("admin@cinema.com", "AdminPass123")
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_upload_image_admin_only(self):
        url = upload_image_url(self.movie.id)
        image = generate_image_file()

        self.authenticate("test@cinema.com", "testpass")
        res = self.client.post(url, {"image": image}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        self.authenticate("admin@cinema.com", "AdminPass123")
        image = generate_image_file()
        res = self.client.post(url, {"image": image}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
