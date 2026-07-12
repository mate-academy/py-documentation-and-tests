import tempfile
import os

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from PIL import Image

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")


def detail_url(movie_id: int):
    return reverse("cinema:movie-detail", args=[movie_id])


def sample_movie(**kwargs) -> Movie:
    defaults = {
        "title": "Sample Movie",
        "description": "Sample Description",
        "duration": 90,
    }
    defaults.update(kwargs)
    return Movie.objects.create(**defaults)


class UnauthenticatedMovieApiTests(APITestCase):
    def test_auth_required_for_list(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="test@user.com",
            password="testpassword123",
        )
        self.client.force_authenticate(self.user)

        self.genre_action = Genre.objects.create(name="Action")
        self.genre_comedy = Genre.objects.create(name="Comedy")
        self.actor_john = Actor.objects.create(first_name="John", last_name="Doe")
        self.actor_jane = Actor.objects.create(first_name="Jane", last_name="Smith")

        self.movie1 = sample_movie(title="Die Hard")
        self.movie2 = sample_movie(title="Superbad")

        self.movie1.genres.add(self.genre_action)
        self.movie1.actors.add(self.actor_john)

        self.movie2.genres.add(self.genre_comedy)
        self.movie2.actors.add(self.actor_jane)

    def test_list_movies(self):
        res = self.client.get(MOVIE_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_title(self):
        res = self.client.get(MOVIE_URL, {"title": "hard"})

        serializer1 = MovieListSerializer(self.movie1)
        serializer2 = MovieListSerializer(self.movie2)

        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

    def test_filter_movies_by_genres(self):
        res = self.client.get(MOVIE_URL, {"genres": f"{self.genre_action.id}"})

        serializer1 = MovieListSerializer(self.movie1)
        serializer2 = MovieListSerializer(self.movie2)

        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

    def test_filter_movies_by_actors(self):
        res = self.client.get(MOVIE_URL, {"actors": f"{self.actor_jane.id}"})

        serializer1 = MovieListSerializer(self.movie1)
        serializer2 = MovieListSerializer(self.movie2)

        self.assertNotIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)

    def test_retrieve_movie_detail(self):
        url = detail_url(self.movie1.id)
        res = self.client.get(url)

        serializer = MovieDetailSerializer(self.movie1)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Forbidden Movie",
            "description": "Forbidden",
            "duration": 100,
        }
        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            email="admin@cinema.com",
            password="adminpassword123",
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        genre = Genre.objects.create(name="Drama")
        actor = Actor.objects.create(first_name="Brad", last_name="Pitt")

        payload = {
            "title": "Fight Club",
            "description": "First rule of Fight Club...",
            "duration": 139,
            "genres": [genre.id],
            "actors": [actor.id],
        }

        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        movie = Movie.objects.get(id=res.data["id"])
        self.assertEqual(movie.title, payload["title"])
        self.assertEqual(movie.genres.count(), 1)
        self.assertEqual(movie.actors.count(), 1)


class MovieImageUploadTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            email="admin_img@cinema.com",
            password="adminpassword123",
        )
        self.client.force_authenticate(self.user)
        self.movie = sample_movie()

    def tearDown(self):
        self.movie.image.delete()

    def test_upload_image_to_movie(self):
        url = reverse("cinema:movie-upload-image", args=[self.movie.id])

        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(url, {"image": ntf}, format="multipart")

        self.movie.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)
        self.assertTrue(os.path.exists(self.movie.image.path))

    def test_upload_image_bad_request(self):
        url = reverse("cinema:movie-upload-image", args=[self.movie.id])
        res = self.client.post(url, {"image": "not_an_image"}, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
