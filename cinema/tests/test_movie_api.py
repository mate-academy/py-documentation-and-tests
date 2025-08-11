import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer
from cinema.views import MovieViewSet

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


class UnauthenticatedMovieAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_authentication_required(self) -> None:
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@gmail.com", password="test12345"
        )
        self.client.force_authenticate(self.user)

        genre_1 = sample_genre()
        self.genre_2 = sample_genre(name="Horror")
        actor_1 = sample_actor()
        self.actor_2 = sample_actor(first_name="Test", last_name="Test")

        movie_1 = sample_movie()
        movie_1.genres.add(genre_1)
        movie_1.actors.add(actor_1)
        self.movie_1 = movie_1

        movie_2 = sample_movie(title="Test", description="Test", duration=80)
        movie_2.genres.add(self.genre_2)
        movie_2.actors.add(self.actor_2)
        self.movie_2 = movie_2

    def test_movie_list(self) -> None:
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)
        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_retrieve_movie_by_title_filter(self) -> None:
        serializer = MovieListSerializer(self.movie_2)

        res = self.client.get(
            MOVIE_URL,
            {"title": "Test"}
        )
        self.assertEqual(len(res.data), 1)
        self.assertIn(serializer.data, res.data)

    def test_retrieve_movie_by_genres_filter(self) -> None:

        serializer = MovieListSerializer(self.movie_2)

        res = self.client.get(
            MOVIE_URL,
            {"genres": f"{self.genre_2.id}"}
        )
        self.assertEqual(len(res.data), 1)
        self.assertIn(serializer.data, res.data)

    def test_retrieve_movie_by_actors_filter(self) -> None:

        serializer = MovieListSerializer(self.movie_2)

        res = self.client.get(
            MOVIE_URL,
            {"actors": f"{self.actor_2.id}"}
        )
        self.assertEqual(len(res.data), 1)
        self.assertIn(serializer.data, res.data)

    def test_retrieve_movie_detail(self) -> None:
        res = self.client.get(detail_url(self.movie_2.id))
        serializer = MovieDetailSerializer(self.movie_2)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self) -> None:
        payload = {
            "title": "Test",
            "description": "Test",
            "duration": 70,
        }
        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_params_to_ints(self) -> None:
        qs = "1,2,3,4,5"
        result = MovieViewSet._params_to_ints(qs)
        self.assertEqual(result, [1, 2, 3, 4, 5])


class AdminMovieAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            email="test@gmail.com", password="test12345"
        )
        self.client.force_authenticate(self.user)

        self.payload = {
            "title": "Test",
            "description": "Test",
            "duration": 70,
        }

    def test_create_movie(self) -> None:
        res = self.client.post(MOVIE_URL, self.payload)
        movie = Movie.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        for key in self.payload:
            self.assertEqual(self.payload[key], getattr(movie, key))

    def test_create_movie_with_genres_and_actors(self) -> None:
        genre_1 = sample_genre()
        actor_1 = sample_actor()
        payload = self.payload.copy()
        payload["genres"] = genre_1.id
        payload["actors"] = actor_1.id

        res = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=res.data["id"])
        genre = movie.genres.all()
        actor = movie.actors.all()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn(genre_1, genre)
        self.assertIn(actor_1, actor)
