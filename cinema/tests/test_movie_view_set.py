import io
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from PIL import Image

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer


def create_image_file():
    """Helper to generate an in-memory image"""
    file = io.BytesIO()
    image = Image.new("RGB", (100, 100), "blue")
    image.save(file, "JPEG")
    file.name = "test.jpg"
    file.seek(0)
    return file


class MovieViewSetTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="user@example.com", password="pass123"
        )
        self.admin = get_user_model().objects.create_superuser(
            email="admin@example.com", password="adminpass"
        )
        self.genre = Genre.objects.create(name="Action")
        self.actor = Actor.objects.create(first_name="Tom", last_name="Hanks")

        self.movie = Movie.objects.create(
            title="Saving Private Ryan",
            description="WWII drama",
            duration=120,
        )
        self.movie.genres.add(self.genre)
        self.movie.actors.add(self.actor)

        self.movie_list_url = reverse("cinema:movie-list")

    # ------------------------
    # LIST & RETRIEVE
    # ------------------------

    def test_list_movies(self):
        self.client.force_authenticate(self.user)
        url = self.movie_list_url
        res = self.client.get(url)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_retrieve_movie(self):
        self.client.force_authenticate(self.user)
        url = reverse("cinema:movie-detail", args=[self.movie.id])
        res = self.client.get(url)

        serializer = MovieDetailSerializer(self.movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    # ------------------------
    # FILTERING
    # ------------------------

    def test_filter_movies_by_title(self):
        self.client.force_authenticate(self.user)
        res = self.client.get(self.movie_list_url, {"title": "Saving"})
        movies = res.data
        self.assertIn(self.movie.title, [m["title"] for m in movies])

    def test_filter_movies_by_genre(self):
        self.client.force_authenticate(self.user)
        res = self.client.get(self.movie_list_url, {"genres": str(self.genre.id)})
        movies = res.data
        self.assertIn(self.movie.title, [m["title"] for m in movies])

    def test_filter_movies_by_actor(self):
        self.client.force_authenticate(self.user)
        res = self.client.get(self.movie_list_url, {"actors": str(self.actor.id)})
        movies = res.data
        self.assertIn(self.movie.title, [m["title"] for m in movies])

    # ------------------------
    # CREATE
    # ------------------------

    def test_create_movie_admin_only(self):
        self.client.force_authenticate(user=self.admin)
        payload = {
            "title": "Forrest Gump",
            "description": "Life story",
            "duration": 140,
            "genres": [self.genre.id],
            "actors": [self.actor.id],
        }
        res = self.client.post(self.movie_list_url, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Movie.objects.filter(title="Forrest Gump").exists())

    def test_create_movie_forbidden_for_non_admin(self):
        self.client.force_authenticate(user=self.user)
        payload = {
            "title": "Forrest Gump",
            "description": "Life story",
            "duration": 140,
            "genres": [self.genre.id],
            "actors": [self.actor.id],
        }
        res = self.client.post(self.movie_list_url, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    # ------------------------
    # UPLOAD IMAGE
    # ------------------------

    def test_upload_image_success(self):
        self.client.force_authenticate(user=self.admin)
        url = reverse("cinema:movie-upload-image", args=[self.movie.id])
        img_file = create_image_file()

        res = self.client.post(url, {"image": img_file}, format="multipart")
        self.movie.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(bool(self.movie.image))

    def test_upload_image_invalid(self):
        self.client.force_authenticate(user=self.admin)
        url = reverse("cinema:movie-upload-image", args=[self.movie.id])

        res = self.client.post(url, {"image": "not-an-image"}, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

