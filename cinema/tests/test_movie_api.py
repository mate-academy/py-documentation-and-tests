import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor
from cinema.serializers import MovieDetailSerializer, MovieListSerializer

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


class UnauthenticatedMovieApiTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)

    def test_movie_list(self):
        movie = sample_movie()
        movie.actors.add(sample_actor())
        movie.genres.add(sample_genre())

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_movie_filtering_by_title(self):
        movie_without_name = sample_movie()
        movie_with_name = sample_movie(title="Test movie name")

        res = self.client.get(
            MOVIE_URL, {"title": "name"}
        )

        serializer_movie_without_name = MovieListSerializer(movie_without_name)
        serializer_movie_with_name = MovieListSerializer(movie_with_name)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer_movie_with_name.data, res.data)
        self.assertNotIn(serializer_movie_without_name.data, res.data)

    def test_movie_filtering_by_genres(self):
        movie_without_genre = sample_movie()
        movie_with_genre_1 = sample_movie(title="Movie name 1")
        movie_with_genre_2 = sample_movie(title="Movie name 2")

        genre_1 = sample_genre(name="Genre 1")
        genre_2 = sample_genre(name="Genre 2")

        movie_with_genre_1.genres.add(genre_1)
        movie_with_genre_2.genres.add(genre_2)

        res = self.client.get(
            MOVIE_URL, {"genres": f"{genre_1.id},{genre_2.id}"}
        )

        serializer_movie_without_genre = MovieListSerializer(
            movie_without_genre
        )
        serializer_movie_with_genre_1 = MovieListSerializer(movie_with_genre_1)
        serializer_movie_with_genre_2 = MovieListSerializer(movie_with_genre_2)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer_movie_with_genre_1.data, res.data)
        self.assertIn(serializer_movie_with_genre_2.data, res.data)
        self.assertNotIn(serializer_movie_without_genre.data, res.data)

    def test_movie_filtering_by_actors(self):
        movie_without_actor = sample_movie()
        movie_with_actor_1 = sample_movie(title="Movie name 1")
        movie_with_actor_2 = sample_movie(title="Movie name 2")

        actor_1 = sample_actor(first_name="First", last_name="Last")
        actor_2 = sample_actor(first_name="Test", last_name="Test")

        movie_with_actor_1.actors.add(actor_1)
        movie_with_actor_2.actors.add(actor_2)

        res = self.client.get(
            MOVIE_URL, {"actors": f"{actor_1.id},{actor_2.id}"}
        )

        serializer_movie_without_actor = MovieListSerializer(
            movie_without_actor
        )
        serializer_movie_with_actor_1 = MovieListSerializer(movie_with_actor_1)
        serializer_movie_with_actor_2 = MovieListSerializer(movie_with_actor_2)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer_movie_with_actor_1.data, res.data)
        self.assertIn(serializer_movie_with_actor_2.data, res.data)
        self.assertNotIn(serializer_movie_without_actor.data, res.data)

    def test_movie_retrieve(self):
        movie = sample_movie()
        movie.actors.add(sample_actor())
        movie.genres.add(sample_genre())

        movie = Movie.objects.first()
        serializer = MovieDetailSerializer(movie)

        res = self.client.get(detail_url(movie.id))

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Sample movie",
            "description": "Sample description",
            "duration": 90,
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        payload = {
            "title": "Sample movie",
            "description": "Sample description",
            "duration": 90,
        }

        res = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.first()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_create_movie_with_genres(self):
        genre_1 = sample_genre(name="Genre 1")
        genre_2 = sample_genre(name="Genre 2")

        payload = {
            "title": "Sample movie",
            "description": "Sample description",
            "duration": 90,
            "genres": [genre_1.id, genre_2.id]
        }

        res = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.first()
        genres = movie.genres.all()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn(genre_1, genres)
        self.assertIn(genre_2, genres)
        self.assertEqual(genres.count(), 2)

    def test_create_movie_with_actors(self):
        actor_1 = sample_actor(first_name="First", last_name="Last")
        actor_2 = sample_actor(first_name="Test", last_name="Test")

        payload = {
            "title": "Sample movie",
            "description": "Sample description",
            "duration": 90,
            "actors": [actor_1.id, actor_2.id]
        }

        res = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.first()
        actors = movie.actors.all()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn(actor_1, actors)
        self.assertIn(actor_2, actors)
        self.assertEqual(actors.count(), 2)
