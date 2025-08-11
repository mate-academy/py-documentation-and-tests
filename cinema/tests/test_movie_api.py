import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor
from cinema.serializers import MovieDetailSerializer
from cinema.serializers import MovieListSerializer

MOVIE_URL = reverse("cinema:movie-list")
MOVIE_SESSION_URL = reverse("cinema:moviesession-list")


def sample_movie(**params):
    defaults = {
        "title": "Sample movie",
        "description": "Sample description",
        "duration": 90,
    }
    defaults.update(params)

    return Movie.objects.create(**defaults)


def sample_genre(**params):
    defaults = {
        "name": "Drama",
    }
    defaults.update(params)

    return Genre.objects.create(**defaults)


def sample_actor(**params):
    defaults = {"first_name": "George", "last_name": "Clooney"}
    defaults.update(params)

    return Actor.objects.create(**defaults)


def sample_movie_session(**params):
    cinema_hall = CinemaHall.objects.create(
        name="Blue", rows=20, seats_in_row=20
    )

    defaults = {
        "show_time": "2022-06-02 14:00:00",
        "movie": None,
        "cinema_hall": cinema_hall,
    }
    defaults.update(params)

    return MovieSession.objects.create(**defaults)


def image_upload_url(movie_id):
    """Return URL for recipe image upload"""
    return reverse("cinema:movie-upload-image", args=[movie_id])


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


class MovieImageUploadTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)
        self.movie = sample_movie()
        self.genre = sample_genre()
        self.actor = sample_actor()
        self.movie_session = sample_movie_session(movie=self.movie)

    def tearDown(self):
        self.movie.image.delete()

    def test_upload_image_to_movie(self):
        """Test uploading an image to movie"""
        url = image_upload_url(self.movie.id)
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
        """Test uploading an invalid image"""
        url = image_upload_url(self.movie.id)
        res = self.client.post(url, {"image": "not image"}, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_image_to_movie_list(self):
        url = MOVIE_URL
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(
                url,
                {
                    "title": "Title",
                    "description": "Description",
                    "duration": 90,
                    "genres": [1],
                    "actors": [1],
                    "image": ntf,
                },
                format="multipart",
            )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(title="Title")
        self.assertFalse(movie.image)

    def test_image_url_is_shown_on_movie_detail(self):
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(detail_url(self.movie.id))

        self.assertIn("image", res.data)

    def test_image_url_is_shown_on_movie_list(self):
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(MOVIE_URL)

        self.assertIn("image", res.data[0].keys())

    def test_image_url_is_shown_on_movie_session_detail(self):
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(MOVIE_SESSION_URL)

        self.assertIn("movie_image", res.data[0].keys())


class UnauthenticatedUserTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_get(self):
        response = self.client.get(MOVIE_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_post(self):
        payload = {}
        response = self.client.post(MOVIE_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedUserTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@gmail.com",
            password="<PASSWORD>",
        )
        self.client.force_authenticate(self.user)
        self.movie_1 = sample_movie(title="Movie1")
        self.movie_2 = sample_movie(title="Movie2")
        self.movie_3 = sample_movie(title="Movie3")

    def test_movies_list(self):
        movie_1 = sample_movie()
        movie_2 = sample_movie()

        response = self.client.get(MOVIE_URL)

        serializer_1 = MovieListSerializer(movie_1)
        serializer_2 = MovieListSerializer(movie_2)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(serializer_1.data, response.data)
        self.assertIn(serializer_2.data, response.data)

    def test_filter_movies_by_actors_list(self):
        actor_1 = sample_actor(first_name="Nicolas")
        actor_2 = sample_actor(first_name="John")

        self.movie_1.actors.add(actor_1)
        self.movie_2.actors.add(actor_2)

        movie_serializer_1 = MovieListSerializer(self.movie_1)
        movie_serializer_2 = MovieListSerializer(self.movie_2)
        movie_serializer_3 = MovieListSerializer(self.movie_3)

        response = self.client.get(MOVIE_URL, {"actors": f"{actor_1.id}"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(movie_serializer_1.data, response.data)
        self.assertNotIn(movie_serializer_2.data, response.data)
        self.assertNotIn(movie_serializer_3.data, response.data)

    def test_filter_movies_by_genres_list(self):
        genre_1 = sample_genre(name="Action")
        genre_2 = sample_genre(name="1-g")

        self.movie_1.genres.add(genre_1)
        self.movie_2.genres.add(genre_2)

        movie_serializer_1 = MovieListSerializer(self.movie_1)
        movie_serializer_2 = MovieListSerializer(self.movie_2)
        movie_serializer_3 = MovieListSerializer(self.movie_3)

        response = self.client.get(MOVIE_URL, {"genres": f"{genre_1.id}"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(movie_serializer_1.data, response.data)
        self.assertNotIn(movie_serializer_2.data, response.data)
        self.assertNotIn(movie_serializer_3.data, response.data)

    def test_filter_movies_by_title_list(self):
        movie_serializer_1 = MovieListSerializer(self.movie_1)
        movie_serializer_2 = MovieListSerializer(self.movie_2)

        response = self.client.get(MOVIE_URL, {"title": self.movie_1.title})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(movie_serializer_1.data, response.data)
        self.assertNotIn(movie_serializer_2.data, response.data)

    def test_retrieve(self):
        movie_serializer = MovieDetailSerializer(self.movie_1)

        response = self.client.get(detail_url(self.movie_1.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, movie_serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "fdsfd",
            "description": "Afs",
            "duration": 100,
        }

        response = self.client.post(MOVIE_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminUserTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.super_user = get_user_model().objects.create_superuser(
            email="admin@gmail.com",
            password="<PASSWORD>",
            is_superuser=True,
        )
        self.client.force_authenticate(self.super_user)

    def test_create_movie(self):
        payload = {
            "title": "fdsfd",
            "description": "Afs",
            "duration": 100,
        }

        response = self.client.post(MOVIE_URL, payload)
        movie_queryset = Movie.objects.filter(title="fdsfd")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(movie_queryset.exists())
        movie = movie_queryset.first()
        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_create_movie_with_actors(self):
        actor_1 = sample_actor(first_name="Nicolas")
        actor_2 = sample_actor(first_name="John")

        payload = {
            "title": "fdsfd",
            "description": "Afs",
            "duration": 100,
            "actors": [actor_1.id, actor_2.id],
        }

        response = self.client.post(MOVIE_URL, payload)

        movie_queryset = Movie.objects.filter(title="fdsfd")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(movie_queryset.exists())

        movie = movie_queryset.first()
        actors = movie.actors.all()

        self.assertEqual(actors.count(), 2)
        self.assertIn(actor_1, actors)
        self.assertIn(actor_2, actors)

    def test_create_movie_with_genres(self):
        genre_1 = sample_genre(name="Action")
        genre_2 = sample_genre(name="1-g")

        payload = {
            "title": "fdsfd",
            "description": "Afs",
            "duration": 100,
            "genres": [genre_1.id, genre_2.id],
        }

        response = self.client.post(MOVIE_URL, payload)
        movie_queryset = Movie.objects.filter(title="fdsfd")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(movie_queryset.exists())

        movie = movie_queryset.first()
        genres = movie.genres.all()

        self.assertEqual(genres.count(), 2)
        self.assertIn(genre_1, genres)
        self.assertIn(genre_2, genres)

    def test_delete_movie(self):
        movie = sample_movie()
        response = self.client.delete(detail_url(movie))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(Movie.objects.count(), 1)





