import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
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


class UnauthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(MOVIE_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        call_command("loaddata", "cinema_service_db_data.json")
        client = APIClient()
        client.force_authenticate(get_user_model().objects.get(id=1))
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img1 = Image.new("RGB", (10, 10))
            img2 = Image.new("RGB", (10, 10))
            img1.save(ntf, format="JPEG")
            img2.save(ntf, format="JPEG")
            ntf.seek(0)
            client.post(
                image_upload_url(1), {"image": ntf}, format="multipart"
            )
            client.post(
                image_upload_url(2), {"image": ntf}, format="multipart"
            )

    def tearDown(self):
        movie = Movie.objects.get(id=1)
        if movie.image:
            movie.image.delete()

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="batman@bat.com", password="WhereIsDetonator_123"
        )
        self.client.force_authenticate(self.user)

    @override_settings(MEDIA_URL="http://testserver/media/")
    def test_should_return_all_movies_list(self):
        response = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_filter_movies_by_genres(self):
        movie_without_genres = Movie.objects.get(id=1)
        movie_without_genres.genres.clear()
        serializer_without_genres = MovieListSerializer(movie_without_genres)
        serializer_with_genres_1 = MovieListSerializer(Movie.objects.get(id=2))
        serializer_with_genres_2 = MovieListSerializer(Movie.objects.get(id=3))

        response = self.client.get(MOVIE_URL, {"genres": "2,4"})

        self.assertIn(serializer_with_genres_1.data, response.data)
        self.assertIn(serializer_with_genres_2.data, response.data)
        self.assertNotIn(serializer_without_genres.data, response.data)

    def test_filter_movies_by_actors(self):
        movie_without_actors = Movie.objects.get(id=1)
        movie_without_actors.actors.clear()
        serializer_without_actors = MovieListSerializer(movie_without_actors)
        serializer_with_actors_1 = MovieListSerializer(Movie.objects.get(id=2))
        serializer_with_actors_2 = MovieListSerializer(Movie.objects.get(id=3))

        response = self.client.get(MOVIE_URL, {"actors": "2,4"})

        self.assertIn(serializer_with_actors_1.data, response.data)
        self.assertIn(serializer_with_actors_2.data, response.data)
        self.assertNotIn(serializer_without_actors.data, response.data)

    def test_filter_movies_by_title(self):
        serializer_matched_1 = MovieListSerializer(Movie.objects.get(id=2))
        serializer_not_matched = MovieListSerializer(Movie.objects.get(id=3))

        response = self.client.get(MOVIE_URL, {"title": "ep"})

        self.assertIn(serializer_matched_1.data, response.data)
        self.assertNotIn(serializer_not_matched.data, response.data)

    @override_settings(MEDIA_URL="http://testserver/media/")
    def test_retrieve_movie_detail(self):
        url = detail_url(1)

        response = self.client.get(url)

        serializer = MovieDetailSerializer(Movie.objects.get(id=1))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "custom movie",
            "description": "custom description",
            "duration": 180,
            "genres": [1, 2, 3],
            "actors": [1, 2, 3],
        }

        response = self.client.post(MOVIE_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("loaddata", "cinema_service_db_data.json")

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(get_user_model().objects.get(id=1))

    def test_create_movie_with_genres_and_actors(self):
        payload = {
            "title": "custom movie",
            "description": "custom description",
            "duration": 180,
            "genres": [1, 2, 3],
            "actors": [1, 2, 3],
        }

        response = self.client.post(MOVIE_URL, payload)
        movie = (
            Movie.objects.filter(id=response.data["id"])
            .prefetch_related("genres", "actors")
            .first()
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(movie.title, payload["title"])
        self.assertEqual(movie.description, payload["description"])
        self.assertEqual(movie.duration, payload["duration"])
        self.assertEqual(
            list(movie.genres.values_list("id", flat=True)), payload["genres"]
        )
        self.assertEqual(
            list(movie.actors.values_list("id", flat=True)), payload["actors"]
        )

    def test_create_movie_without_genres_should_return_400(self):
        payload = {
            "title": "custom movie",
            "description": "custom description",
            "duration": 180,
            "actors": [1, 2, 3],
        }

        response = self.client.post(MOVIE_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_movie_without_actors_should_return_400(self):
        payload = {
            "title": "custom movie",
            "description": "custom description",
            "duration": 180,
            "genres": [1, 2, 3],
        }

        response = self.client.post(MOVIE_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_movie_not_allowed(self):
        url = detail_url(1)

        response = self.client.delete(url)

        self.assertEqual(
            response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )
