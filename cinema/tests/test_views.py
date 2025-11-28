import os
import tempfile

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer
from cinema.tests.test_movie_api import image_upload_url

MOVIE_URL = reverse("cinema:movie-list")


def detail_url(movie_id):
    """Create and return a movie detail URL"""
    return reverse("cinema:movie-detail", args=[movie_id])


def sample_movie(**params):
    """Create and return a sample movie"""
    defaults = {
        "title": "Sample Movie",
        "description": "Sample description",
        "duration": 120,
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)


def sample_genre(**params):
    """Create and return a sample genre"""
    defaults = {"name": "Action"}
    defaults.update(params)
    return Genre.objects.create(**defaults)


def sample_actor(**params):
    """Create and return a sample actor"""
    defaults = {
        "first_name": "John",
        "last_name": "Doe",
    }
    defaults.update(params)
    return Actor.objects.create(**defaults)


class UnauthenticatedMovieApiTests(TestCase):
    """Test unauthenticated movie API access"""

    def setUp(self):
        self.client = APIClient()
        self.movie = sample_movie()

    def test_auth_required(self):
        """Test that authentication is required"""
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_upload_image_to_movie(self):
        """Test uploading an image to movie"""
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(url, {"image": ntf}, format="multipart")
        self.movie.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    """Test authenticated movie API access"""

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
        sample_movie(title="Another Movie")

        res = self.client.get(MOVIE_URL)

        movies = Movie.objects.all().order_by("id")
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)

    def test_retrieve_movie_detail(self):
        """Test retrieving a movie detail"""
        movie = sample_movie()
        genre = sample_genre()
        actor = sample_actor()
        movie.genres.add(genre)
        movie.actors.add(actor)

        url = detail_url(movie.id)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["title"], movie.title)

    def test_create_movie_forbidden_for_non_admin(self):
        """Test creating a movie is forbidden for non-admin users"""
        genre = sample_genre()
        actor = sample_actor()

        payload = {
            "title": "New Movie",
            "description": "New description",
            "duration": 90,
            "genres": [genre.id],
            "actors": [actor.id],
        }
        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_filter_movies_by_title(self):
        """Test filtering movies by title"""
        movie1 = sample_movie(title="The Matrix")
        movie2 = sample_movie(title="Matrix Reloaded")
        movie3 = sample_movie(title="Avatar")

        res = self.client.get(MOVIE_URL, {"title": "Matrix"})

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie3)

        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_filter_movies_by_genres(self):
        """Test filtering movies by genres"""
        genre1 = sample_genre(name="Action")
        genre2 = sample_genre(name="Comedy")

        movie1 = sample_movie(title="Action Movie")
        movie1.genres.add(genre1)

        movie2 = sample_movie(title="Comedy Movie")
        movie2.genres.add(genre2)

        movie3 = sample_movie(title="Both Genres")
        movie3.genres.add(genre1, genre2)

        res = self.client.get(MOVIE_URL, {"genres": str(genre1.id)})

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie3)

        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)
        self.assertIn(serializer3.data, res.data)

    def test_filter_movies_by_actors(self):
        """Test filtering movies by actors"""
        actor1 = sample_actor(first_name="Tom", last_name="Hanks")
        actor2 = sample_actor(first_name="Brad", last_name="Pitt")

        movie1 = sample_movie(title="Movie 1")
        movie1.actors.add(actor1)

        movie2 = sample_movie(title="Movie 2")
        movie2.actors.add(actor2)

        res = self.client.get(MOVIE_URL, {"actors": str(actor1.id)})

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)

        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

    def test_filter_movies_by_multiple_genres(self):
        """Test filtering movies by multiple genres"""
        genre1 = sample_genre(name="Action")
        genre2 = sample_genre(name="Sci-Fi")

        movie1 = sample_movie(title="Action Only")
        movie1.genres.add(genre1)

        movie2 = sample_movie(title="Sci-Fi Only")
        movie2.genres.add(genre2)

        movie3 = sample_movie(title="Both Genres")
        movie3.genres.add(genre1, genre2)

        res = self.client.get(MOVIE_URL, {"genres": f"{genre1.id},{genre2.id}"})

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie3)

        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertIn(serializer3.data, res.data)

    def test_filter_movies_by_multiple_actors(self):
        """Test filtering movies by multiple actors"""
        actor1 = sample_actor(first_name="Tom", last_name="Hanks")
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


class AdminMovieApiTests(TestCase):
    """Test admin movie API access"""

    def setUp(self):
        self.client = APIClient()
        self.movie = sample_movie()
        self.user = get_user_model().objects.create_user(
            email="admin@test.com",
            password="testpass123",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        """Test creating a movie as admin"""
        genre = sample_genre()
        actor = sample_actor()

        payload = {
            "title": "New Movie",
            "description": "New description",
            "duration": 90,
            "genres": [genre.id],
            "actors": [actor.id],
        }
        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(id=res.data["id"])
        self.assertEqual(movie.title, payload["title"])
        self.assertEqual(movie.duration, payload["duration"])
        self.assertIn(genre, movie.genres.all())
        self.assertIn(actor, movie.actors.all())

    def test_admin_upload_image_to_movie(self):
        """Test uploading an image to movie"""
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(url, {"image": ntf}, format="multipart")
        self.movie.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
