import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor
from cinema.views import MovieViewSet
from cinema.serializers import (
    MovieListSerializer,
    MovieDetailSerializer,
    MovieSerializer,
    MovieImageSerializer
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
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    """Test authenticated users can access movie API endpoints"""

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@email.com",
            password="password1029"
        )
        self.client.force_authenticate(self.user)
        self.movie = sample_movie()
        self.genre = sample_genre()
        self.actor = sample_actor()
        self.movie.genres.add(self.genre)
        self.movie.actors.add(self.actor)

    def test_retrieve_movies(self):
        """Test retrieving a list of movies"""
        sample_movie(title="Movie 2")
        sample_movie(title="Movie 3")

        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 3)

    def test_retrieve_movie_detail(self):
        """Test retrieving a movie detail"""
        url = detail_url(self.movie.id)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["title"], self.movie.title)
        self.assertEqual(res.data["description"], self.movie.description)
        self.assertEqual(res.data["duration"], self.movie.duration)
        self.assertEqual(len(res.data["genres"]), 1)
        self.assertEqual(len(res.data["actors"]), 1)

    def test_create_movie_forbidden(self):
        """Test that regular users cannot create movies"""
        payload = {
            "title": "New Movie",
            "description": "New Description",
            "duration": 120,
            "genres": [self.genre.id],
            "actors": [self.actor.id]
        }
        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_filter_movies_by_title(self):
        """Test filtering movies by title"""
        movie1 = sample_movie(title="Action movie")
        movie2 = sample_movie(title="Drama movie")
        movie3 = sample_movie(title="Comedy")

        res = self.client.get(MOVIE_URL, {"title": "movie"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Get titles from the response data
        titles = [movie["title"] for movie in res.data]
        # Check that the filtered movies are in the response
        self.assertIn(movie1.title, titles)
        self.assertIn(movie2.title, titles)
        # Check that the non-matching movie is not in the response
        self.assertNotIn(movie3.title, titles)

    def test_filter_movies_by_genres(self):
        """Test filtering movies by genres"""
        movie1 = sample_movie(title="Movie 1")
        movie2 = sample_movie(title="Movie 2")
        genre1 = sample_genre(name="Action")
        genre2 = sample_genre(name="Comedy")
        movie1.genres.add(genre1)
        movie2.genres.add(genre2)

        res = self.client.get(MOVIE_URL, {"genres": f"{genre1.id}"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], movie1.title)

    def test_filter_movies_by_actors(self):
        """Test filtering movies by actors"""
        movie1 = sample_movie(title="Movie 1")
        movie2 = sample_movie(title="Movie 2")
        actor1 = sample_actor(first_name="Brad", last_name="Pitt")
        actor2 = sample_actor(first_name="Tom", last_name="Cruise")
        movie1.actors.add(actor1)
        movie2.actors.add(actor2)

        res = self.client.get(MOVIE_URL, {"actors": f"{actor1.id}"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], movie1.title)

    def test_filter_movies_by_multiple_params(self):
        """Test filtering movies by multiple parameters"""
        movie1 = sample_movie(title="Action movie")
        movie2 = sample_movie(title="Drama movie")
        movie3 = sample_movie(title="Action comedy")
        # Use unique names for genres
        genre1 = sample_genre(name="Action Genre")
        genre2 = sample_genre(name="Drama Genre")
        actor1 = sample_actor(first_name="Brad", last_name="Pitt")
        actor2 = sample_actor(first_name="Tom", last_name="Cruise")

        movie1.genres.add(genre1)
        movie1.actors.add(actor1)
        movie2.genres.add(genre2)
        movie2.actors.add(actor2)
        movie3.genres.add(genre1)
        movie3.actors.add(actor2)

        res = self.client.get(
            MOVIE_URL,
            {
                "title": "action",
                "genres": f"{genre1.id}",
                "actors": f"{actor1.id}"
            }
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], movie1.title)


class AdminMovieApiTests(TestCase):
    """Tests for movie API that require admin privileges"""

    def setUp(self):
        self.client = APIClient()
        self.admin_user = get_user_model().objects.create_superuser(
            email="admin@example.com",
            password="password123"
        )
        self.client.force_authenticate(self.admin_user)
        self.movie = sample_movie()
        self.genre = sample_genre()
        self.actor = sample_actor()

    def test_create_movie_successful(self):
        """Test creating a new movie as admin"""
        payload = {
            "title": "New Movie",
            "description": "New Description",
            "duration": 120,
            "genres": [self.genre.id],
            "actors": [self.actor.id]
        }
        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(id=res.data["id"])
        self.assertEqual(movie.title, payload["title"])
        self.assertEqual(movie.description, payload["description"])
        self.assertEqual(movie.duration, payload["duration"])
        genres = movie.genres.all()
        self.assertEqual(len(genres), 1)
        self.assertIn(self.genre, genres)
        actors = movie.actors.all()
        self.assertEqual(len(actors), 1)
        self.assertIn(self.actor, actors)

    def test_create_movie_invalid(self):
        """Test creating a new movie with invalid payload as admin"""
        payload = {"title": ""}
        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


class MovieParamsToIntsTests(TestCase):
    """Test the _params_to_ints static method in MovieViewSet"""

    def test_convert_string_to_int_list(self):
        """Test converting a comma-separated string to a list of integers"""

        result = MovieViewSet._params_to_ints("1,2,3")
        self.assertEqual(result, [1, 2, 3])

    def test_convert_single_value_to_int_list(self):
        """Test converting a single string value to a list with one integer"""

        result = MovieViewSet._params_to_ints("5")
        self.assertEqual(result, [5])


class MovieSerializerClassTests(TestCase):
    """Test the get_serializer_class method in MovieViewSet"""

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@email.com",
            password="password1029"
        )
        self.client.force_authenticate(self.user)

    def test_get_serializer_class_for_list_action(self):
        """Test that MovieListSerializer is returned for list action"""

        view = MovieViewSet()
        view.action = "list"

        self.assertEqual(view.get_serializer_class(), MovieListSerializer)

    def test_get_serializer_class_for_retrieve_action(self):
        """Test that MovieDetailSerializer is returned for retrieve action"""

        view = MovieViewSet()
        view.action = "retrieve"

        self.assertEqual(view.get_serializer_class(), MovieDetailSerializer)

    def test_get_serializer_class_for_upload_image_action(self):
        """
        Test that MovieImageSerializer is returned for upload_image action
        """

        view = MovieViewSet()
        view.action = "upload_image"

        self.assertEqual(view.get_serializer_class(), MovieImageSerializer)

    def test_get_serializer_class_for_default_action(self):
        """Test that MovieSerializer is returned for default action"""

        view = MovieViewSet()
        view.action = "create"

        self.assertEqual(view.get_serializer_class(), MovieSerializer)


class AdminRequiredTests(TestCase):
    """Test that admin permissions are required for certain actions"""

    def setUp(self):
        self.client = APIClient()
        self.movie = sample_movie()

        # Regular user
        self.user = get_user_model().objects.create_user(
            email="user@example.com",
            password="password123"
        )

        # Admin user
        self.admin_user = get_user_model().objects.create_superuser(
            email="admin@example.com",
            password="password123"
        )

    def test_upload_image_admin_required(self):
        """Test that only admin users can upload images"""
        url = image_upload_url(self.movie.id)

        # Authenticate as a regular user
        self.client.force_authenticate(self.user)

        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(url, {"image": ntf}, format="multipart")

        # Regular user should get forbidden
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        # Authenticate as an admin user
        self.client.force_authenticate(self.admin_user)

        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(url, {"image": ntf}, format="multipart")

        # Admin user should succeed
        self.assertEqual(res.status_code, status.HTTP_200_OK)
