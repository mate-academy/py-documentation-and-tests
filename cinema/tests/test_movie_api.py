import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor
from cinema.serializers import (MovieListSerializer,
                                MovieDetailSerializer,
                                MovieSerializer)

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
    cinema_hall = CinemaHall.objects.create(name="Blue", rows=20,
                                            seats_in_row=20)

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


class UnauthenticatedCinemaAPITests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self):
        result = self.client.get(path=MOVIE_URL)
        self.assertEqual(result.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedCinemaAPITests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@test.ua", "testpassword"
        )
        self.client.force_authenticate(self.user)

    def test_list_movies(self):
        sample_movie()
        movie_with_genre_and_actors = sample_movie()

        actor = sample_actor(first_name="Test", last_name="Actor")
        genre = sample_genre(name="Test genre")

        movie_with_genre_and_actors.actors.add(actor)
        movie_with_genre_and_actors.genres.add(genre)

        result = self.client.get(path=MOVIE_URL)

        movies = Movie.objects.all()
        serialiser = MovieListSerializer(movies, many=True)
        self.assertEqual(result.status_code, status.HTTP_200_OK)
        self.assertEqual(result.data, serialiser.data)

    def test_filter_movies(self):
        movie = sample_movie()
        movie_with_params = sample_movie(title="TestTitle")

        actor = sample_actor()
        genre1 = sample_genre(name="TestGenre1")
        genre2 = sample_genre(name="TestGenre2")

        movie_with_params.actors.add(actor)
        movie_with_params.genres.add(genre1)
        movie_with_params.genres.add(genre2)

        resp1 = self.client.get(MOVIE_URL, {"actors": f"{actor.id}"})
        resp2 = self.client.get(MOVIE_URL,
                                {"genres": f"{genre1.id},{genre2.id}"})
        resp3 = self.client.get(MOVIE_URL,
                                {"title": f"{movie_with_params.title}"})

        serializer1 = MovieListSerializer(movie_with_params)
        serializer2 = MovieListSerializer(movie)

        self.assertIn(serializer1.data, resp1.data)
        self.assertNotIn(serializer2.data, resp1.data)
        self.assertIn(serializer1.data, resp2.data)
        self.assertNotIn(serializer2.data, resp2.data)
        self.assertIn(serializer1.data, resp3.data)
        self.assertNotIn(serializer2.data, resp3.data)

    def test_retrieve_movies(self):
        movie = sample_movie()

        movie.actors.add(sample_actor())
        movie.genres.add(sample_genre())

        url = detail_url(movie.id)

        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_movie_create_forbidden(self):
        payload = {
            "description": "Movie",
            "duration": 100
        }

        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminCinemaAPITests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@test.ua",
            "adminpassword",
            is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_movie_created(self):
        genre = sample_genre()
        payload = {
            "title": "Movie",
            "description": "MovieAdmin",
            "duration": 100,
            "genres": genre.id
        }

        res = self.client.post(MOVIE_URL, payload)
        print(res.data)
        movie = Movie.objects.get(id=res.data["id"])
        serializer = MovieSerializer(movie)
        genres = movie.genres.all()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(genres.count(), 1)
        self.assertIn(genre, genres)
        self.assertEqual(serializer.data, res.data)

    def test_admin_update_movie_not_allowed(self):
        movie = sample_movie()
        genre = sample_genre()
        payload_to_put = {
            "title": "Test Put Title",
            "description": "Update description",
            "duration": 120,
            "genres": genre.id
        }
        payload_to_patch = {
            "title": "Test Patch Title",
        }

        res1 = self.client.put(detail_url(movie.id), payload_to_put)
        res2 = self.client.patch(detail_url(movie.id), payload_to_patch)

        self.assertEqual(res1.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(res2.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_admin_delete_movie_not_allowed(self):
        movie = sample_movie()

        res = self.client.delete(detail_url(movie.id))

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
