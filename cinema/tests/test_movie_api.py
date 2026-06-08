import tempfile
import os
from PIL import Image

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor, CinemaHall, MovieSession
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")
MOVIE_SESSION_URL = reverse("cinema:moviesession-list")


def detail_url(movie_id):
    """Return URL for a specific movie detail view"""
    return reverse("cinema:movie-detail", args=[movie_id])


def image_upload_url(movie_id):
    """Return URL for movie image upload action"""
    return reverse("cinema:movie-upload-image", args=[movie_id])


def sample_movie(**params):
    """Create and return a sample movie"""
    defaults = {
        "title": "Sample movie",
        "description": "Sample description",
        "duration": 90,
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)


def sample_genre(**params):
    """Create and return a sample genre"""
    defaults = {"name": "Drama"}
    defaults.update(params)
    return Genre.objects.create(**defaults)


def sample_actor(**params):
    """Create and return a sample actor"""
    defaults = {"first_name": "George", "last_name": "Clooney"}
    defaults.update(params)
    return Actor.objects.create(**defaults)


def sample_movie_session(**params):
    """Create and return a sample movie session"""
    cinema_hall = CinemaHall.objects.create(
        name="Blue", rows=20, seats_in_row=20
    )
    defaults = {
        "show_time": "2026-06-02 14:00:00",
        "movie": None,
        "cinema_hall": cinema_hall,
    }
    defaults.update(params)
    return MovieSession.objects.create(**defaults)


class UnauthenticatedMovieApiTests(TestCase):
    """Test suite for unauthenticated users (Access should be denied)"""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required_for_list(self):
        """Test that retrieving movie list requires authentication (returns 401)"""
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_auth_required_for_detail(self):
        """Test that retrieving movie detail requires authentication (returns 401)"""
        movie = sample_movie()
        res = self.client.get(detail_url(movie.id))
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_movie_unauthorized_forbidden(self):
        """Test that unauthenticated user cannot create a movie (returns 401)"""
        payload = {
            "title": "Unauthorized Movie",
            "description": "No auth",
            "duration": 100,
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    """Test suite for regular authenticated users"""

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user@test.com",
            password="testpassword123",
        )
        self.client.force_authenticate(self.user)

    def test_list_movies(self):
        """Test retrieving a list of movies by an authenticated user"""
        sample_movie(title="Movie 1")
        sample_movie(title="Movie 2")

        res = self.client.get(MOVIE_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_title(self):
        """Test filtering movies by title query parameter"""
        movie1 = sample_movie(title="Batman")
        movie2 = sample_movie(title="Superman")

        res = self.client.get(MOVIE_URL, {"title": "bat"})

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)

        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

    def test_filter_movies_by_genres(self):
        """Test filtering movies by genres IDs query parameter"""
        movie_with_genre = sample_movie(title="Drama Movie")
        movie_without_genre = sample_movie(title="Action Movie")
        genre1 = sample_genre(name="Drama")
        genre2 = sample_genre(name="Action")
        movie_with_genre.genres.add(genre1)
        movie_without_genre.genres.add(genre2)

        res = self.client.get(MOVIE_URL, {"genres": f"{genre1.id}"})

        serializer_with = MovieListSerializer(movie_with_genre)
        serializer_without = MovieListSerializer(movie_without_genre)

        self.assertIn(serializer_with.data, res.data)
        self.assertNotIn(serializer_without.data, res.data)

    def test_filter_movies_by_actors(self):
        """Test filtering movies by actors IDs query parameter"""
        movie_with_actor = sample_movie(title="Movie with Star")
        movie_without_actor = sample_movie(title="Indie Movie")
        actor1 = sample_actor(first_name="John", last_name="Doe")
        actor2 = sample_actor(first_name="Jane", last_name="Smith")
        movie_with_actor.actors.add(actor1)
        movie_without_actor.actors.add(actor2)

        res = self.client.get(MOVIE_URL, {"actors": f"{actor1.id}"})

        serializer_with = MovieListSerializer(movie_with_actor)
        serializer_without = MovieListSerializer(movie_without_actor)

        self.assertIn(serializer_with.data, res.data)
        self.assertNotIn(serializer_without.data, res.data)

    def test_retrieve_movie_detail(self):
        """Test retrieving detailed information about a specific movie"""
        movie = sample_movie()
        genre = sample_genre()
        actor = sample_actor()
        movie.genres.add(genre)
        movie.actors.add(actor)

        url = detail_url(movie.id)
        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_authenticated_forbidden(self):
        """Test that a regular authenticated user is forbidden from creating a movie"""
        payload = {
            "title": "Regular User Movie",
            "description": "Should fail",
            "duration": 120,
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTests(TestCase):
    """Test suite for administrator users (Full access & image operations)"""

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            email="admin@myproject.com",
            password="password",
        )
        self.client.force_authenticate(self.user)
        self.movie = sample_movie()
        self.genre = sample_genre()
        self.actor = sample_actor()
        self.movie_session = sample_movie_session(movie=self.movie)

    def tearDown(self):
        if self.movie.image:
            self.movie.image.delete()

    def test_create_movie(self):
        """Test creating a movie by an admin user"""
        genre = sample_genre(name="Comedy")
        actor = sample_actor(first_name="Brad", last_name="Pitt")
        payload = {
            "title": "An Admin Movie",
            "description": "Great description",
            "duration": 130,
            "genres": [genre.id],
            "actors": [actor.id],
        }

        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        movie = Movie.objects.get(id=res.data["id"])
        self.assertEqual(movie.title, payload["title"])
        self.assertEqual(movie.genres.first().id, genre.id)

    def test_upload_image_to_movie(self):
        """Test successfully uploading an image to a movie"""
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
        """Test uploading an invalid image file returns a bad request error"""
        url = image_upload_url(self.movie.id)
        res = self.client.post(url, {"image": "not image"}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_image_to_movie_list_ignored(self):
        """Test that image field is ignored when creating a movie via the main list endpoint"""
        url = MOVIE_URL
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(
                url,
                {
                    "title": "Title Without Image",
                    "description": "Description",
                    "duration": 90,
                    "genres": [self.genre.id],
                    "actors": [self.actor.id],
                    "image": ntf,
                },
                format="multipart",
            )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(title="Title Without Image")
        self.assertFalse(movie.image)

    def test_image_url_is_shown_on_movie_detail(self):
        """Test that movie image URL is present in the movie detail view response"""
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(detail_url(self.movie.id))

        self.assertIn("image", res.data)

    def test_image_url_is_shown_on_movie_list(self):
        """Test that movie image field is present in the movie list view response"""
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(MOVIE_URL)

        self.assertIn("image", res.data[0].keys())

    def test_image_url_is_shown_on_movie_session_detail(self):
        """Test that movie image field is present in the movie session view response"""
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(MOVIE_SESSION_URL)

        self.assertIn("movie_image", res.data[0].keys())