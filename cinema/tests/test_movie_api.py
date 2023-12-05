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


class UnauthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(MOVIE_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@user.com", password="user12345"
        )
        self.client.force_authenticate(self.user)

        self.initial_genre = sample_genre()
        self.initial_actor = sample_actor()

        self.initial_movie1 = sample_movie()
        self.initial_movie2 = sample_movie()

        self.initial_movie2.genres.add(self.initial_genre)
        self.initial_movie2.actors.add(self.initial_actor)

    def test_movie_list(self):
        response = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_movie_retrieve(self):
        url = detail_url(self.initial_movie2.id)
        response = self.client.get(url)

        serializer = MovieDetailSerializer(self.initial_movie2)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_movie_list_with_filter_by_title(self):
        movie = sample_movie(title="Movie")

        response = self.client.get(MOVIE_URL, {"title": "Movie"})

        serializer_initial = MovieListSerializer(self.initial_movie2)
        serializer_local = MovieListSerializer(movie)

        self.assertNotIn(serializer_initial.data, response.data)
        self.assertIn(serializer_local.data, response.data)

    def test_movie_list_with_filter_by_genres(self):
        genre1 = sample_genre(name="Genre1")
        genre2 = sample_genre(name="Genre2")

        movie1 = sample_movie()
        movie2 = sample_movie()

        movie1.genres.add(genre1)
        movie2.genres.add(genre2)

        response = self.client.get(
            MOVIE_URL, {"genres": f"{self.initial_genre.id},{genre2.id}"}
        )

        serializer_initial = MovieListSerializer(self.initial_movie2)
        serializer_local1 = MovieListSerializer(movie1)
        serializer_local2 = MovieListSerializer(movie2)

        self.assertIn(serializer_initial.data, response.data)
        self.assertIn(serializer_local1.data, response.data)
        self.assertNotIn(serializer_local2.data, response.data)

    def test_movie_list_with_filter_by_actors(self):
        actor = sample_actor(first_name="Actor")
        self.initial_movie1.actors.add(self.initial_actor)

        movie = sample_movie()
        movie.actors.add(actor)

        response = self.client.get(MOVIE_URL, {
            "actors": f"{self.initial_actor.id}"
        })

        serializer_initial = MovieListSerializer(self.initial_movie2)
        serializer_local = MovieListSerializer(movie)

        self.assertIn(serializer_initial.data, response.data)
        self.assertNotIn(serializer_local.data, response.data)

    def test_movie_list_forbidden_to_post(self):
        movie = {
            "title": "Movie",
            "description": "Desctiption",
            "duration": 100,
        }
        response = self.client.post(MOVIE_URL, movie)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_movie_retrieve_forbidden_to_update(self):
        movie = {
            "title": "Movie",
            "description": "Description",
            "duration": 100,
        }
        url = detail_url(self.initial_movie2.id)
        response = self.client.put(url, movie)
        response2 = self.client.patch(url, movie)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response2.status_code, status.HTTP_403_FORBIDDEN)

    def test_movie_retrieve_forbidden_to_delete(self):
        url = detail_url(self.initial_movie2.id)
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@user.com",
            password="user12345",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)

        self.initial_movie = sample_movie()

    def test_movie_list_create_bus(self):
        genre = sample_genre()
        actor = sample_actor()
        movie = {
            "title": "Movie",
            "description": "Description",
            "duration": 100,
            "genres": [genre.id],
            "actors": [actor.id],
        }

        response = self.client.post(MOVIE_URL, movie)
        movie = Movie.objects.get(id=response.data["id"])

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(movie["title"], getattr(movie, "title"))
        self.assertEqual(movie["description"], getattr(movie, "description"))
        self.assertEqual(movie["duration"], getattr(movie, "duration"))

        self.assertIn(genre, movie.genres.all())
        self.assertIn(actor, movie.actors.all())

    def test_movie_retrieve_not_allowed_to_update(self):
        url = detail_url(self.initial_movie.id)
        movie = {
            "title": "Movie",
            "description": "Description",
            "duration": 100,
        }

        response = self.client.patch(url, movie)

        self.assertEqual(response.status_code,
                         status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_movie_retrieve_not_allowed_to_delete(self):
        url = detail_url(self.initial_movie.id)

        response = self.client.delete(url)

        self.assertEqual(response.status_code,
                         status.HTTP_405_METHOD_NOT_ALLOWED)
