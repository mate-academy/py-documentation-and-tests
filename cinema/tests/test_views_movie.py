from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from cinema.models import Movie, Genre, Actor


MOVIE_URL = reverse("cinema:movie-list")


def movie_detail_url(movie_id: int) -> str:
    return reverse("cinema:movie-detail", args=[movie_id])


def movie_image_url(movie_id: int) -> str:
    return reverse("cinema:movie-upload-image", args=[movie_id])


class MovieViewSetTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            email="user@test.com",
            password="password123"
        )
        cls.admin = get_user_model().objects.create_superuser(
            email="admin@test.com",
            password="admin123"
        )

        cls.genre = Genre.objects.create(name="Action")
        cls.actor = Actor.objects.create(
            first_name="Tom",
            last_name="Hardy"
        )

        cls.movie = Movie.objects.create(
            title="Test Movie",
            description="Description",
            duration=120
        )
        cls.movie.genres.add(cls.genre)
        cls.movie.actors.add(cls.actor)

    def authenticate_user(self):
        self.client.force_authenticate(self.user)

    def authenticate_admin(self):
        self.client.force_authenticate(self.admin)

    def test_list_movies(self):
        self.authenticate_user()
        response = self.client.get(MOVIE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_movie(self):
        self.authenticate_user()
        response = self.client.get(movie_detail_url(self.movie.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_filter_movies_by_title(self):
        self.authenticate_user()
        response = self.client.get(MOVIE_URL, {"title": "Test"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_filter_movies_by_genres(self):
        self.authenticate_user()
        response = self.client.get(
            MOVIE_URL,
            {"genres": str(self.genre.id)}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_filter_movies_by_actors(self):
        self.authenticate_user()
        response = self.client.get(
            MOVIE_URL,
            {"actors": str(self.actor.id)}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_movie_forbidden_for_user(self):
        self.authenticate_user()
        response = self.client.post(
            MOVIE_URL,
            {
                "title": "New Movie",
                "description": "Description",
                "duration": 90,
                "genres": [self.genre.id],
                "actors": [self.actor.id],
            }
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_movie_allowed_for_admin(self):
        self.authenticate_admin()
        response = self.client.post(
            MOVIE_URL,
            {
                "title": "Admin Movie",
                "description": "Description",
                "duration": 100,
                "genres": [self.genre.id],
                "actors": [self.actor.id],
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_upload_image_forbidden_for_user(self):
        self.authenticate_user()
        response = self.client.post(movie_image_url(self.movie.id))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
