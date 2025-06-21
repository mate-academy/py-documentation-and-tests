import os
import shutil
import tempfile

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")
TEMP_MEDIA_ROOT = tempfile.mkdtemp()


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=(movie_id,))


class UnauthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(MOVIE_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class MovieDataTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.genre_1 = Genre.objects.create(name="Comedy")
        cls.genre_2 = Genre.objects.create(name="Drama")
        cls.actor_1 = Actor.objects.create(first_name="Jack", last_name="Jackson")
        cls.actor_2 = Actor.objects.create(first_name="Jill", last_name="Jillson")
        cls.actor_3 = Actor.objects.create(first_name="Romance", last_name="Romance")

        cls.movie_1 = Movie.objects.create(
            title="Sample Movie",
            description="Sample Movie Description",
            duration=60,
        )
        cls.movie_1.actors.add(cls.actor_1, cls.actor_2)
        cls.movie_1.genres.add(cls.genre_1)

        cls.movie_2 = Movie.objects.create(
            title="German movie",
            description="The best movie",
            duration=40,
        )
        cls.movie_2.actors.add(cls.actor_1)
        cls.movie_2.genres.add(cls.genre_2)

        cls.movie_3 = Movie.objects.create(
            title="Really interesting movie",
            description="The best movie",
            duration=40,
        )
        cls.movie_3.actors.add(cls.actor_2, cls.actor_3)
        cls.movie_3.genres.add(cls.genre_2)

    def test_filter_movies_by_actors_and_title(self):
        response = self.client.get(
            MOVIE_URL,
            {
                "actors": str(self.actor_2.id),
                "title": "sample",
            },
        )

        included = [self.movie_1]
        excluded = [self.movie_2, self.movie_3]

        included_serialized = MovieListSerializer(included, many=True).data
        response_data = response.data

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        for item in included_serialized:
            self.assertIn(item, response_data)

        excluded_serialized = MovieListSerializer(excluded, many=True).data
        for item in excluded_serialized:
            self.assertNotIn(item, response_data)

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com",
            password="testpass",
        )
        self.client.force_authenticate(user=self.user)


class AuthenticatedMovieApiTests(MovieDataTest):

    def test_movie_list(self):

        response = self.client.get(MOVIE_URL)
        movie = Movie.objects.all()
        serializer = MovieListSerializer(movie, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_filter_movies_by_actors(self):
        response = self.client.get(
            MOVIE_URL,
            {"actors": str(self.actor_2.id)},
        )

        included = [self.movie_1, self.movie_3]
        excluded = [self.movie_2]

        included_serialized = MovieListSerializer(included, many=True).data
        response_data = response.data

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for item in included_serialized:
            self.assertIn(item, response_data)

        excluded_serialized = MovieListSerializer(excluded, many=True).data
        for item in excluded_serialized:
            self.assertNotIn(item, response_data)

    def test_filter_movies_by_title(self):
        response = self.client.get(
            MOVIE_URL,
            {"title": "sam"},
        )

        included = [self.movie_1]
        excluded = [self.movie_2, self.movie_3]

        included_serialized = MovieListSerializer(included, many=True).data
        response_data = response.data

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for item in included_serialized:
            self.assertIn(item, response_data)

        excluded_serialized = MovieListSerializer(excluded, many=True).data
        for item in excluded_serialized:
            self.assertNotIn(item, response_data)

    def test_filter_movies_by_genres(self):
        response = self.client.get(
            MOVIE_URL,
            {"genres": str(self.genre_2.id)},
        )

        included = [self.movie_2, self.movie_3]
        excluded = [self.movie_1]

        included_serialized = MovieListSerializer(included, many=True).data
        response_data = response.data

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for item in included_serialized:
            self.assertIn(item, response_data)

        excluded_serialized = MovieListSerializer(excluded, many=True).data
        for item in excluded_serialized:
            self.assertNotIn(item, response_data)

    def test_retrieve_movie_detail(self):
        url = detail_url(self.movie_3.id)
        response = self.client.get(url)
        serializer = MovieDetailSerializer(self.movie_3)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Sample Movie Title",
            "description": "Sample Movie Description",
            "duration": 60,
        }
        response = self.client.post(MOVIE_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class AdminMovieTests(MovieDataTest):
    def setUp(self):
        super().setUp()
        self.admin_user = get_user_model().objects.create_user(
            email="admin@test.com",
            password="adminpass",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.admin_user)

    def test_create_movie(self):
        payload = {
            "title": "Sample Movie Title",
            "description": "Sample Movie Description",
            "duration": 60,
            "genres": [self.genre_1.id],
            "actors": [self.actor_1.id, self.actor_2.id],
        }
        response = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=response.data["id"])

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(movie.title, payload["title"])
        self.assertEqual(movie.description, payload["description"])
        self.assertEqual(movie.duration, payload["duration"])

        self.assertEqual(
            list(movie.genres.values_list("id", flat=True)), payload["genres"]
        )
        self.assertEqual(
            sorted(list(movie.actors.values_list("id", flat=True))),
            sorted(payload["actors"]),
        )

    def tearDown(self):
        if os.path.exists(TEMP_MEDIA_ROOT):
            shutil.rmtree(TEMP_MEDIA_ROOT)

    def test_upload_image_to_movie(self):

        url = reverse("cinema:movie-upload-image", args=[self.movie_1.id])
        with tempfile.NamedTemporaryFile(suffix=".jpg") as image_file:
            image = Image.new("RGB", (100, 100))
            image.save(image_file, format="JPEG")
            image_file.seek(0)
            response = self.client.post(url, {"image": image_file}, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.movie_1.refresh_from_db()
        self.assertTrue(bool(self.movie_1.image))

    def test_delete_movie_not_allowed(self):
        url = detail_url(self.movie_2.id)

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
