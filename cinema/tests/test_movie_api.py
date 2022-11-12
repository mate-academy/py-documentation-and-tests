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


class UnauthenticatedMovieTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_required_authenticated(self):
        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedUserMovieTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

        self.user = get_user_model().objects.create_user(
            email="user@mail.com",
            password="user12345"
        )
        self.client.force_authenticate(self.user)

    def test_list_movies(self):
        sample_movie()
        sample_movie()

        resp = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data, serializer.data)

    def test_filter_by_genres(self):
        movie_1 = sample_movie()
        movie_2 = sample_movie()
        movie_without_genre = sample_movie()
        genre_1 = sample_genre(name="genre_1")
        genre_2 = sample_genre(name="genre_2")
        movie_1.genres.add(genre_1)
        movie_2.genres.add(genre_2)

        resp = self.client.get(MOVIE_URL, {"genres": f"{genre_1.id}, {genre_2.id}"})

        serializer_1 = MovieListSerializer(movie_1)
        serializer_2 = MovieListSerializer(movie_2)
        serializer_3 = MovieListSerializer(movie_without_genre)

        self.assertNotIn(serializer_3.data, resp.data)
        self.assertIn(serializer_1.data, resp.data)
        self.assertIn(serializer_2.data, resp.data)

    def test_filter_by_actor(self):
        movie_1 = sample_movie()
        movie_2 = sample_movie()
        movie_without_actor = sample_movie()
        actor_1 = sample_actor(
            first_name="Name_1",
            last_name="Lastname_1"
        )
        actor_2 = sample_actor(
            first_name="Name_2",
            last_name="Lastname_2"
        )
        movie_1.actors.add(actor_1)
        movie_2.actors.add(actor_2)

        resp = self.client.get(MOVIE_URL, {"actors": f"{actor_1.id},{actor_2.id}"})

        serializer_1 = MovieListSerializer(movie_1)
        serializer_2 = MovieListSerializer(movie_2)
        serializer_3 = MovieListSerializer(movie_without_actor)

        self.assertIn(serializer_1.data, resp.data)
        self.assertIn(serializer_2.data, resp.data)
        self.assertNotIn(serializer_3.data, resp.data)

    def test_filter_by_title(self):
        movie_1 = sample_movie(title="Test")
        movie_with_default_title = sample_movie()

        resp = self.client.get(MOVIE_URL, {"title": f"{movie_1.title}"})

        serializer_1 = MovieListSerializer(movie_1)
        serializer_2 = MovieListSerializer(movie_with_default_title)

        self.assertIn(serializer_1.data, resp.data)
        self.assertNotIn(serializer_2.data, resp.data)

    def test_retrieve_movie(self):
        movie = sample_movie()

        url = detail_url(movie.id)
        resp = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(serializer.data, resp.data)

    def test_post_movie_forbidden(self):
        payload = {
            "title": "Sample movie",
            "description": "Sample description",
            "duration": 90,
        }

        resp = self.client.post(MOVIE_URL, payload)

        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_patch_movie_forbidden(self):
        movie = sample_movie()
        payload = {
            "title": "Another title"
        }

        url = detail_url(movie.id)

        resp = self.client.patch(url, payload)

        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            email="admin@mail.com",
            password="user12345",
            is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_post_movie_allowed(self):
        actor = sample_actor()
        genre = sample_genre()
        pay_load = {
            "title": "Sample movie",
            "description": "Sample description",
            "duration": 90,
            "actors": [actor.id],
            "genres": [genre.id]
        }

        resp = self.client.post(MOVIE_URL, pay_load)

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        movie = Movie.objects.get(id=resp.data["id"])
        actors = movie.actors.all()
        genres = movie.genres.all()

        self.assertEqual(actors.count(), 1)
        self.assertEqual(genres.count(), 1)
        self.assertIn(actor, actors)
        self.assertIn(genre, genres)

    def test_patch_forbidden(self):
        movie = sample_movie()
        pay_load = {
            "title": "New title"
        }
        url = detail_url(movie.id)

        resp = self.client.patch(url, pay_load)

        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_movie(self):
        movie = sample_movie()

        url = detail_url(movie.id)

        resp = self.client.delete(url)

        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)