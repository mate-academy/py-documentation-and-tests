from io import BytesIO
from PIL import Image
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from cinema.models import Movie, Genre, Actor
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

User = get_user_model()


def get_test_image():
    file = BytesIO()
    image = Image.new("RGB", (100, 100), color="red")
    image.save(file, "JPEG")
    file.seek(0)
    return SimpleUploadedFile(
        "test.jpg", file.read(), content_type="image/jpeg"
    )

class MovieViewSetTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="admin.user@cinema.com", password="1qazcde3", is_staff=True
        )
        self.client = APIClient()
        token_url = reverse("token_obtain_pair")
        response = self.client.post(
            token_url,
            {"email": self.user.email, "password": "1qazcde3"},
            format="json"
        )
        self.token = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

        self.genre = Genre.objects.create(name="Action")
        self.actor = Actor.objects.create(first_name="John", last_name="Doe")
        self.movie = Movie.objects.create(
            title="Test Movie", description="Desc", duration=120
        )
        self.movie.genres.add(self.genre)
        self.movie.actors.add(self.actor)

    def test_list_movies(self):
        url = reverse("cinema:movie-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_filter_movies_by_title(self):
        url = reverse("cinema:movie-list") + "?title=Test"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_filter_movies_by_genres(self):
        url = reverse("cinema:movie-list") + f"?genres={self.genre.id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_filter_movies_by_actors(self):
        url = reverse("cinema:movie-list") + f"?actors={self.actor.id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_create_movie_admin(self):
        url = reverse("cinema:movie-list")
        data = {
            "title": "New Movie",
            "description": "Desc",
            "duration": 100,
            "genres": [self.genre.id],
            "actors": [self.actor.id]
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_retrieve_movie(self):
        url = reverse("cinema:movie-detail", args=[self.movie.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)



    def test_upload_image_admin(self):
        url = reverse("cinema:movie-upload-image", args=[self.movie.id])
        image = get_test_image()
        response = self.client.post(url, {"image": image}, format="multipart")
        self.assertIn(
            response.status_code,
            [status.HTTP_200_OK, status.HTTP_201_CREATED]
        )
