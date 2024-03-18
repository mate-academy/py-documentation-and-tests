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


class UnauthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_movie_list_auth_required(self):
        response = self.client.get(MOVIE_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="bababubu@buba.bu",
            password="ba6a_bub0"
        )
        self.client.force_authenticate(self.user)

        self.actor = sample_actor(first_name="Michael", last_name="Popkin")
        self.genre = sample_genre(name="Documentary")
        self.movie = sample_movie(title="Brother Man")

        self.movie.actors.add(self.actor)
        self.movie.genres.add(self.genre)

    def test_movie_list_response(self):
        sample_movie()

        response = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_movie_filter_by_title(self):
        no_bro_movie = sample_movie()
        response = self.client.get(MOVIE_URL, {"title": "bro"})

        serializer_bro = MovieListSerializer(self.movie)
        serializer_no_bro = MovieListSerializer(no_bro_movie)

        self.assertIn(serializer_bro.data, response.data)
        self.assertNotIn(serializer_no_bro.data, response.data)

    def test_movie_filter_by_genre_id(self):
        no_genre_movie = sample_movie()
        response = self.client.get(MOVIE_URL, {"genres": self.genre.id})

        serializer_genre = MovieListSerializer(self.movie)
        serializer_no_genre = MovieListSerializer(no_genre_movie)

        self.assertIn(serializer_genre.data, response.data)
        self.assertNotIn(serializer_no_genre.data, response.data)

    def test_movie_filter_by_actor_id(self):
        no_actor_movie = sample_movie()
        response = self.client.get(MOVIE_URL, {"actors": self.actor.id})

        serializer_actor = MovieListSerializer(self.movie)
        serializer_no_actor = MovieListSerializer(no_actor_movie)

        self.assertIn(serializer_actor.data, response.data)
        self.assertNotIn(serializer_no_actor.data, response.data)

    def test_movie_detail_response(self):
        response = self.client.get(detail_url(self.movie.id))

        serializer = MovieDetailSerializer(self.movie)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(serializer.data, response.data)

    def test_create_movie_is_forbidden(self):
        payload = {
            "title": "More guns, more power",
            "description": "You never know who is the boss",
            "duration": 116
        }
        response = self.client.post(MOVIE_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="bababoss@admin.me",
            password="ba6a_bub0",
            is_staff=True
        )
        self.client.force_authenticate(self.user)

        self.actor = sample_actor(first_name="Pedro", last_name="Kozulya")
        self.genre = sample_genre(name="Detective")
        self.movie = sample_movie(title="No gain, no pain")

        self.movie.actors.add(self.actor)
        self.movie.genres.add(self.genre)

    def test_valid_movie_creation(self):
        payload = {
            "title": "More guns, more power",
            "description": "You never know who is the boss",
            "duration": 116,
            "actors": [self.actor.id],
            "genres": [self.genre.id]
        }
        response = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=response.data["id"])

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        serializer = MovieDetailSerializer(movie)
        detail_response = self.client.get(detail_url(movie.id))

        self.assertEqual(serializer.data, detail_response.data)

    def test_patch_movie_is_not_allowed(self):
        payload = {"title": "No pain, no gain"}
        url = detail_url(self.movie.id)

        response = self.client.patch(url, payload)

        self.assertEqual(
            response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def test_put_movie_is_not_allowed(self):
        payload = {
            "title": "Cashier in the supermarket",
            "description": "You never know...",
            "duration": 116,
            "actors": [self.actor.id],
            "genres": [self.genre.id]
        }
        url = detail_url(self.movie.id)

        response = self.client.put(url, payload)

        self.assertEqual(
            response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def test_delete_movie_is_not_allowed(self):
        response = self.client.delete(detail_url(self.movie.id))

        self.assertEqual(
            response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )


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
