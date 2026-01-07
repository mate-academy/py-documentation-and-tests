import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import (
    Movie,
    MovieSession,
    CinemaHall,
    Genre,
    Actor
)
from cinema.serializers import (
    MovieListSerializer,
    MovieDetailSerializer
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
        """Test that authentication is required"""
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_movie_unauthorized(self):
        """Test that unauthenticated user receives 401 for retrieve action"""
        movie = sample_movie()
        url = detail_url(movie.id)

        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_movie_unauthorized(self):
        """Test that unauthenticated user receives 401 for create action"""
        genre = sample_genre()
        actor = sample_actor()

        payload = {
            "title": "New Movie",
            "description": "Description",
            "duration": 120,
            "genres": [genre.id],
            "actors": [actor.id],
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_upload_image_unauthorized(self):
        """
        Test that unauthenticated user
        receives 401 for upload_image action
        """
        movie = sample_movie()
        url = image_upload_url(movie.id)

        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(url, {"image": ntf}, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedNonAdminMovieApiTests(TestCase):
    """Tests for authenticated non-admin users"""

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user@test.com",
            password="testpass123",
        )
        self.client.force_authenticate(self.user)

    def test_upload_image_forbidden_for_non_admin(self):
        """
        Test that authenticated non-admin user
        receives 403 for upload_image action
        """
        movie = sample_movie()
        url = image_upload_url(movie.id)

        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(url, {"image": ntf}, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com",
            password="testpass123",
        )
        self.client.force_authenticate(self.user)

    def test_list_movies(self):
        """Test retrieving a list of movies"""
        sample_movie()
        sample_movie(title="Another movie")

        res = self.client.get(MOVIE_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_title(self):
        """Test filtering movies by title"""
        movie1 = sample_movie(title="Harry Potter")
        movie2 = sample_movie(title="Lord of the Rings")
        movie3 = sample_movie(title="Harry Potter 2")

        res = self.client.get(MOVIE_URL, {"title": "Harry"})

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie3)

        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)
        self.assertIn(serializer3.data, res.data)

    def test_filter_movies_by_genres(self):
        """Test filtering movies by genres"""
        genre1 = sample_genre(name="Action")
        genre2 = sample_genre(name="Comedy")

        movie1 = sample_movie(title="Movie 1")
        movie1.genres.add(genre1)

        movie2 = sample_movie(title="Movie 2")
        movie2.genres.add(genre2)

        movie3 = sample_movie(title="Movie 3")
        movie3.genres.add(genre1, genre2)

        res = self.client.get(MOVIE_URL, {"genres": f"{genre1.id}"})

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie3)

        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)
        self.assertIn(serializer3.data, res.data)

    def test_filter_movies_by_actors(self):
        """Test filtering movies by actors"""
        actor1 = sample_actor(first_name="Tom", last_name="Cruise")
        actor2 = sample_actor(first_name="Brad", last_name="Pitt")

        movie1 = sample_movie(title="Movie 1")
        movie1.actors.add(actor1)

        movie2 = sample_movie(title="Movie 2")
        movie2.actors.add(actor2)

        movie3 = sample_movie(title="Movie 3")
        movie3.actors.add(actor1, actor2)

        res = self.client.get(
            MOVIE_URL, {"actors": f"{actor1.id},{actor2.id}"}
        )

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie3)

        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertIn(serializer3.data, res.data)

    def test_filter_movies_by_multiple_genres(self):
        """Test filtering movies by multiple genres"""
        genre1 = sample_genre(name="Action")
        genre2 = sample_genre(name="Comedy")
        genre3 = sample_genre(name="Drama")

        movie1 = sample_movie(title="Movie 1")
        movie1.genres.add(genre1, genre2)

        movie2 = sample_movie(title="Movie 2")
        movie2.genres.add(genre2, genre3)

        movie3 = sample_movie(title="Movie 3")
        movie3.genres.add(genre1)

        res = self.client.get(
            MOVIE_URL, {"genres": f"{genre1.id},{genre2.id}"}
        )

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie3)

        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertIn(serializer3.data, res.data)

    def test_retrieve_movie_detail(self):
        """Test retrieving a movie detail"""
        movie = sample_movie()
        movie.genres.add(sample_genre())
        movie.actors.add(sample_actor())

        url = detail_url(movie.id)
        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_retrieve_movie_detail_with_empty_genres_and_actors(self):
        """Test retrieving a movie with no genres or actors"""
        movie = sample_movie()

        url = detail_url(movie.id)
        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)
        self.assertEqual(len(res.data["genres"]), 0)
        self.assertEqual(len(res.data["actors"]), 0)

    def test_filter_movies_no_results(self):
        """Test filtering movies with no matching results"""
        sample_movie(title="Movie 1")
        sample_movie(title="Movie 2")

        res = self.client.get(MOVIE_URL, {"title": "NonExistent"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 0)

    def test_create_movie_forbidden(self):
        """Test that creating movie is forbidden for non-admin"""
        payload = {
            "title": "New Movie",
            "description": "Description",
            "duration": 120,
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@test.com",
            password="testpass123",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)

    def test_create_movie_with_genres_and_actors(self):
        """Test creating a movie with both genres and actors"""
        genre = sample_genre(name="Action")
        actor = sample_actor(first_name="Tom", last_name="Cruise")

        payload = {
            "title": "New Movie",
            "description": "Description",
            "duration": 120,
            "genres": [genre.id],
            "actors": [actor.id],
        }

        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(id=res.data["id"])
        self.assertEqual(movie.genres.count(), 1)
        self.assertEqual(movie.actors.count(), 1)
        self.assertIn(genre, movie.genres.all())
        self.assertIn(actor, movie.actors.all())

    def test_create_movie_without_genres_fails(self):
        """Test that creating movie without genres fails"""
        actor = sample_actor()

        payload = {
            "title": "New Movie",
            "description": "Description",
            "duration": 120,
            "actors": [actor.id],
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("genres", res.data)

    def test_create_movie_without_actors_fails(self):
        """Test that creating movie without actors fails"""
        genre = sample_genre()

        payload = {
            "title": "New Movie",
            "description": "Description",
            "duration": 120,
            "genres": [genre.id],
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("actors", res.data)
