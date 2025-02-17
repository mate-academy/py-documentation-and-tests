from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.reverse import reverse
from django.contrib.auth import get_user_model
from cinema.models import Movie, Genre, Actor
from django.core.files.uploadedfile import SimpleUploadedFile


class MovieViewSetTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            email="testuser@test.com", password="testpassword123"
        )
        cls.admin_user = get_user_model().objects.create_superuser(
            email="adminuser@test.com", password="adminpassword123"
        )

        cls.genre = Genre.objects.create(name="Action")
        cls.actor = Actor.objects.create(first_name="Bruce", last_name="Willis")
        cls.movie = Movie.objects.create(
            title="Die Hard",
            description="A cop must save a building from terrorists",
            duration=132,
        )
        cls.movie.genres.add(cls.genre)
        cls.movie.actors.add(cls.actor)

    def test_movie_list(self):
        url = reverse("cinema:movie-list")

        self.client.force_authenticate(user=self.user)

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(self.movie.title, [movie["title"] for movie in response.data])

    def test_movie_retrieve(self):
        url = reverse("cinema:movie-detail", args=[self.movie.id])

        self.client.force_authenticate(user=self.user)

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], self.movie.title)

    def test_movie_create_by_admin(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("cinema:movie-list")
        data = {
            "title": "Inception",
            "description": "A mind-bending thriller by Christopher Nolan",
            "duration": 148,
            "genres": [self.genre.id],
            "actors": [self.actor.id],
        }
        response = self.client.post(url, data, format="json")

        # Ensure the status code is 201 Created
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["title"], "Inception")
        self.assertEqual(Movie.objects.count(), 2)

    def test_movie_create_by_non_admin(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("cinema:movie-list")
        data = {
            "title": "Inception",
            "description": "A mind-bending thriller by Christopher Nolan",
            "duration": 148,
            "genres": [self.genre.id],
            "actors": [self.actor.id],
        }
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_movie_upload_image_by_non_admin(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("cinema:movie-upload-image", args=[self.movie.id])

        image_file = SimpleUploadedFile(
            "test_image.jpg", b"image_content", content_type="image/jpeg"
        )
        data = {"image": image_file}

        response = self.client.post(url, data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_movie_list_with_filters(self):
        url = reverse("cinema:movie-list")

        self.client.force_authenticate(user=self.user)

        response = self.client.get(url, {"title": "Die Hard"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        response = self.client.get(url, {"genres": self.genre.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        response = self.client.get(url, {"actors": self.actor.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
