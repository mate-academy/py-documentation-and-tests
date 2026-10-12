import tempfile
from io import BytesIO

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image
from rest_framework import status
from rest_framework.test import APIClient
from django.core.files.uploadedfile import SimpleUploadedFile

from cinema.models import Actor, Genre, Movie


class MovieViewSetTests(TestCase):
    def setUp(self):
        self.media_directory = tempfile.TemporaryDirectory()
        self.settings_override = override_settings(
            MEDIA_ROOT=self.media_directory.name,
        )
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.addCleanup(self.media_directory.cleanup)

        self.client = APIClient()
        user_model = get_user_model()

        self.user = user_model.objects.create_user(
            email="user@example.com",
            password="testpassword123",
        )
        self.admin = user_model.objects.create_user(
            email="admin@example.com",
            password="testpassword123",
            is_staff=True,
        )

        self.genre = Genre.objects.create(name="Drama")
        self.other_genre = Genre.objects.create(name="Action")
        self.actor = Actor.objects.create(
            first_name="Test",
            last_name="Actor",
        )
        self.other_actor = Actor.objects.create(
            first_name="Other",
            last_name="Actor",
        )

        self.movie = Movie.objects.create(
            title="The Departed",
            description="A crime drama.",
            duration=151,
        )
        self.movie.genres.add(self.genre)
        self.movie.actors.add(self.actor)

        self.other_movie = Movie.objects.create(
            title="Action Movie",
            description="An action movie.",
            duration=120,
        )
        self.other_movie.genres.add(self.other_genre)
        self.other_movie.actors.add(self.other_actor)

        self.list_url = reverse("cinema:movie-list")
        self.detail_url = reverse(
            "cinema:movie-detail",
            args=[self.movie.pk],
        )

        self.client.force_authenticate(user=self.user)

    def movie_payload(self, title="New Movie"):
        return {
            "title": title,
            "description": "A test movie.",
            "duration": 100,
            "genres": [self.genre.pk],
            "actors": [self.actor.pk],
        }

    def test_list_movies(self):
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_retrieve_movie(self):
        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.movie.pk)
        self.assertEqual(response.data["title"], "The Departed")

    def test_create_movie_as_admin(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            self.list_url,
            self.movie_payload(),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Movie.objects.filter(title="New Movie").exists()
        )

    def test_regular_user_cannot_create_movie(self):
        response = self.client.post(
            self.list_url,
            self.movie_payload(),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_anonymous_user_can_list_movies(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self.list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_filter_movies_by_title(self):
        response = self.client.get(
            self.list_url,
            {"title": "departed"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.movie.pk)

    def test_filter_movies_by_genre(self):
        response = self.client.get(
            self.list_url,
            {"genres": str(self.genre.pk)},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.movie.pk)

    def test_filter_movies_by_actor(self):
        response = self.client.get(
            self.list_url,
            {"actors": str(self.actor.pk)},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.movie.pk)

    def test_filter_movies_by_multiple_genres(self):
        response = self.client.get(
            self.list_url,
            {
                "genres": (
                    f"{self.genre.pk},{self.other_genre.pk}"
                ),
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_upload_movie_image(self):
        self.client.force_authenticate(user=self.admin)

        image_buffer = BytesIO()
        image = Image.new("RGB", (10, 10), color="red")
        image.save(image_buffer, format="PNG")

        upload = SimpleUploadedFile(
            "poster.png",
            image_buffer.getvalue(),
            content_type="image/png",
        )
        url = reverse(
            "cinema:movie-upload-image",
            args=[self.movie.pk],
        )

        response = self.client.post(
            url,
            {"image": upload},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.movie.refresh_from_db()
        self.assertTrue(self.movie.image.name)

    def test_regular_user_cannot_upload_image(self):
        url = reverse(
            "cinema:movie-upload-image",
            args=[self.movie.pk],
        )

        response = self.client.post(url, {}, format="multipart")

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_update_movie_is_not_allowed(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            self.detail_url,
            {"title": "Changed title"},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )


    def test_delete_movie_is_not_allowed(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.delete(self.detail_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )
