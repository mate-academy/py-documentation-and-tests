import io
import tempfile

from PIL import Image
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from cinema.models import Actor, Genre, Movie
from cinema.serializers import MovieDetailSerializer, MovieListSerializer


class MovieViewSetTests(TestCase):
    def setUp(self) -> None:
        cache.clear()
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        settings = self.settings(MEDIA_ROOT=directory.name)
        settings.enable()
        self.addCleanup(settings.disable)
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user@example.com", password="password"
        )
        self.staff = get_user_model().objects.create_superuser(
            email="staff@example.com", password="password"
        )
        self.client.force_authenticate(self.user)
        self.genre = Genre.objects.create(name="Drama")
        self.actor = Actor.objects.create(first_name="Emma", last_name="Watson")
        self.movie = Movie.objects.create(
            title="First Movie", description="Description", duration=100
        )
        self.movie.genres.add(self.genre)
        self.movie.actors.add(self.actor)
        self.url = reverse("cinema:movie-list")
        self.detail = reverse("cinema:movie-detail", args=[self.movie.pk])
        self.upload = reverse("cinema:movie-upload-image", args=[self.movie.pk])

    @staticmethod
    def image() -> SimpleUploadedFile:
        buffer = io.BytesIO()
        Image.new("RGB", (10, 10)).save(buffer, format="JPEG")
        return SimpleUploadedFile(
            "photo.jpg", buffer.getvalue(), content_type="image/jpeg"
        )

    def payload(self) -> dict:
        return {
            "title": "New Movie", "description": "New description",
            "duration": 90, "genres": [self.genre.pk],
            "actors": [self.actor.pk],
        }

    def test_anonymous_access_is_denied(self) -> None:
        self.client.force_authenticate(None)
        for method, url in (
            (self.client.get, self.url),
            (self.client.get, self.detail),
            (self.client.post, self.url),
            (self.client.post, self.upload),
        ):
            self.assertEqual(method(url).status_code, 401)

    def test_list_uses_string_relationships(self) -> None:
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data,
            MovieListSerializer(Movie.objects.all(), many=True).data,
        )
        self.assertEqual(response.data[0]["genres"], ["Drama"])
        self.assertEqual(response.data[0]["actors"], ["Emma Watson"])

    def test_retrieve_uses_nested_relationships(self) -> None:
        response = self.client.get(self.detail)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data, MovieDetailSerializer(self.movie).data
        )
        self.assertEqual(response.data["genres"][0]["name"], "Drama")

    def test_missing_movie_returns_not_found(self) -> None:
        response = self.client.get(
            reverse("cinema:movie-detail", args=[self.movie.pk + 100])
        )
        self.assertEqual(response.status_code, 404)

    def test_regular_user_cannot_create_or_upload(self) -> None:
        self.assertEqual(
            self.client.post(self.url, self.payload()).status_code, 403
        )
        response = self.client.post(
            self.upload, {"image": self.image()}, format="multipart"
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Movie.objects.count(), 1)

    def test_staff_can_create_with_relationships(self) -> None:
        self.client.force_authenticate(self.staff)
        response = self.client.post(
            self.url, self.payload(), format="json"
        )
        self.assertEqual(response.status_code, 201)
        movie = Movie.objects.get(pk=response.data["id"])
        self.assertEqual(list(movie.genres.all()), [self.genre])
        self.assertEqual(list(movie.actors.all()), [self.actor])

    def test_invalid_create_is_rejected(self) -> None:
        self.client.force_authenticate(self.staff)
        for change in (
            {"title": ""}, {"duration": "invalid"},
            {"genres": [9999]}, {"actors": [9999]},
        ):
            with self.subTest(change=change):
                response = self.client.post(
                    self.url, {**self.payload(), **change}, format="json"
                )
                self.assertEqual(response.status_code, 400)
        self.assertEqual(Movie.objects.count(), 1)

    def test_filter_by_title_genres_and_actors(self) -> None:
        Movie.objects.create(
            title="Unrelated", description="Other", duration=90
        )
        for query in (
            {"title": "FIRST"}, {"genres": str(self.genre.pk)},
            {"actors": str(self.actor.pk)},
            {"title": "Movie", "genres": str(self.genre.pk),
             "actors": str(self.actor.pk)},
        ):
            response = self.client.get(self.url, query)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                [movie["id"] for movie in response.data], [self.movie.pk]
            )
        for query in (
            {"title": "absent"}, {"genres": "9999"}, {"actors": "9999"},
        ):
            self.assertEqual(self.client.get(self.url, query).data, [])

    def test_multiple_relationship_matches_do_not_duplicate_movies(self):
        genre = Genre.objects.create(name="Comedy")
        actor = Actor.objects.create(first_name="First", last_name="Actor")
        self.movie.genres.add(genre)
        self.movie.actors.add(actor)
        response = self.client.get(
            self.url,
            {"genres": f"{self.genre.pk},{genre.pk}",
             "actors": f"{self.actor.pk},{actor.pk}"},
        )
        self.assertEqual(len(response.data), 1)

    def test_list_queries_are_bounded(self) -> None:
        for index in range(3):
            movie = Movie.objects.create(
                title=f"Movie {index}", description="Description", duration=90
            )
            movie.genres.add(self.genre)
            movie.actors.add(self.actor)
        with self.assertNumQueries(3):
            self.assertEqual(len(self.client.get(self.url).data), 4)

    def test_unsupported_detail_writes_are_not_allowed(self) -> None:
        self.client.force_authenticate(self.staff)
        for method in (
            self.client.put, self.client.patch, self.client.delete,
        ):
            self.assertEqual(method(self.detail).status_code, 405)
        self.assertTrue(Movie.objects.filter(pk=self.movie.pk).exists())

    def test_staff_image_upload_and_urls(self) -> None:
        self.client.force_authenticate(self.staff)
        response = self.client.post(
            self.upload, {"image": self.image()}, format="multipart"
        )
        self.assertEqual(response.status_code, 200)
        image_url = response.data["image"]
        self.assertTrue(image_url.startswith("http://testserver/media/"))
        self.assertEqual(
            self.client.get(self.detail).data["image"], image_url
        )
        self.assertEqual(
            self.client.get(self.url).data[0]["image"], image_url
        )

    def test_invalid_image_upload(self) -> None:
        self.client.force_authenticate(self.staff)
        response = self.client.post(
            self.upload,
            {"image": SimpleUploadedFile("bad.jpg", b"not an image")},
            format="multipart",
        )
        self.assertEqual(response.status_code, 400)
        self.movie.refresh_from_db()
        self.assertFalse(self.movie.image)

    def test_image_upload_for_missing_movie(self) -> None:
        self.client.force_authenticate(self.staff)
        response = self.client.post(
            reverse("cinema:movie-upload-image", args=[9999]),
            {"image": self.image()}, format="multipart",
        )
        self.assertEqual(response.status_code, 404)

    def test_creation_does_not_accept_image(self) -> None:
        self.client.force_authenticate(self.staff)
        response = self.client.post(
            self.url, {**self.payload(), "image": self.image()},
            format="multipart",
        )
        self.assertEqual(response.status_code, 201)
        self.assertFalse(Movie.objects.get(pk=response.data["id"]).image)
