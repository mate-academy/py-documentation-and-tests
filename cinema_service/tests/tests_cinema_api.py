from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient, APITestCase
from django.urls import reverse
from rest_framework import status
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework_simplejwt.tokens import RefreshToken

from cinema.models import Genre, Actor, Movie


class MovieViewSetTestCase(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            email="admin@domain.com", password="adminpassword"
        )

        refresh = RefreshToken.for_user(self.user)
        self.token = str(refresh.access_token)

        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.token)

        self.genre = Genre.objects.create(name="Action")
        self.actor = Actor.objects.create(first_name="John", last_name="Doe")
        self.movie = Movie.objects.create(
            title="Test Movie",
            description="Test description",
            duration=120
        )
        self.movie.genres.add(self.genre)
        self.movie.actors.add(self.actor)

    def test_list_movies(self):
        url = reverse("cinema:movie-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Test Movie")

    def test_filter_movies_by_genre(self):
        url = reverse("cinema:movie-list")
        response = self.client.get(url, {"genres": [self.genre.id]})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Test Movie")

    def test_filter_movies_by_title(self):
        url = reverse("cinema:movie-list")
        response = self.client.get(url, {"title": "Test Movie"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Test Movie")

    def test_retrieve_movie(self):
        url = reverse("cinema:movie-detail", args=[self.movie.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "Test Movie")

    def test_create_movie(self):
        url = reverse("cinema:movie-list")
        payload = {
            "title": "Test Movie",
            "description": "New description",
            "duration": 130,
            "genres": [self.genre.id],
            "actors": [self.actor.id]
        }

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Movie.objects.count(), 2)
        self.assertEqual(Movie.objects.last().title, "Test Movie")

    def test_upload_movie_image(self):
        url = reverse("cinema:movie-detail", args=[self.movie.id])
        image_path = "/Users/khrypunov/PycharmProjects/py-documentation-and-tests/media/uploads/movies/sample-movie-1b44e4f6-479e-44ca-9af4-bd540db97363.jpg"

        with open(image_path, 'rb') as img_file:
            image = SimpleUploadedFile(
                name="sample-movie-1b44e4f6-479e-44ca-9af4-bd540db97363.jpg",
                content=img_file.read(),
                content_type="image/jpeg"
            )
        response = self.client.post(url, {"image": image}, format="multipart")

        self.assertIn(response.status_code, [status.HTTP_405_METHOD_NOT_ALLOWED])
