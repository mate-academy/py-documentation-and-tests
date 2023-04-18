import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor
from cinema.serializers import (
    MovieListSerializer,
    MovieDetailSerializer,
)

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
    cinema_hall = CinemaHall.objects.create(name="Blue", rows=20, seats_in_row=20)

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


class UnathenticatedMovieApi(TestCase):
    def SetUP(self):
        self.client = APIClient()

    def test_denied_access_for_unathenticated_user(self):
        response = self.client.get(MOVIE_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedUserMovieApi(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@gmail.com", password="testpassword"
        )
        self.client.force_authenticate(user=self.user)

    def test_access_for_athenticated_user(self):
        response = self.client.get(MOVIE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_movies(self):
        movie1 = sample_movie()
        movie2 = sample_movie(title="Test_film2")
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)
        response = self.client.get(MOVIE_URL)
        self.assertEqual(response.data, serializer.data)
        self.assertEqual(len(serializer.data), len(response.data))

    def test_filtering_movies_by_actors(self):
        actor1 = sample_actor(first_name="Jach", last_name="Cloo")
        actor2 = sample_actor(first_name="Test", last_name="Actor")
        movie1 = sample_movie(title="Gladiator")
        movie2 = sample_movie(title="Without actors")
        movie1.actors.add(actor1)
        movie1.actors.add(actor2)

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        response = self.client.get(MOVIE_URL, {"actors": f"{actor1.id}"})
        self.assertIn(serializer1.data, response.data)
        self.assertNotIn(serializer2.data, response.data)

    def test_filtering_movies_by_title(self):
        movie1 = sample_movie(title="Gladiator")
        movie2 = sample_movie(title="Without actors")

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        response = self.client.get(MOVIE_URL, {"title": f"{movie1.title}"})
        self.assertIn(serializer1.data, response.data)
        self.assertNotIn(serializer2.data, response.data)

    def test_filtering_movies_by_genres(self):
        genres1 = sample_genre(name="Comedy")
        genres2 = sample_genre(name="Triller")
        movie1 = sample_movie(title="Gladiator")
        movie2 = sample_movie(title="Without actors")
        movie1.genres.add(genres1)
        movie1.genres.add(genres1)

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        response = self.client.get(MOVIE_URL, {"genres": f"{genres1.id}, {genres2.id}"})
        self.assertIn(serializer1.data, response.data)
        self.assertNotIn(serializer2.data, response.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        response = self.client.get(detail_url(movie.id))
        serializer = MovieDetailSerializer(movie)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_create_movie_not_allowed_for_user(self):
        payload = {"title": "Wolf", "duration": 60, "description": "Test description"}
        response = self.client.post(MOVIE_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieAPI(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            email="admin@gmail.com", password="admin12345"
        )
        self.client.force_authenticate(self.user)

    def test_create_movie_allowed_for_admin(self):
        actor = sample_actor()
        genre = sample_genre()

        payload = {
            "title": "Wolf",
            "duration": 60,
            "description": "Test description",
            "actors": [actor.id],
            "genres": [genre.id],
        }
        response = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=response.data["id"])

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        for key in payload:
            if key == "actors":
                self.assertEqual(payload[key][0], movie.actors.first().id)
            elif key == "genres":
                self.assertEqual(payload[key][0], movie.genres.first().id)
            else:
                self.assertEqual(payload[key], getattr(movie, key))


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
