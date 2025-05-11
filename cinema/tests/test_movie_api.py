import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status
from cinema.views import MovieViewSet

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor

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


#tests for MovieViewSet

class MovieViewSetTests(TestCase):
    """
    Test suite for MovieViewSet functionality.
    
    This test suite covers all CRUD operations, filtering capabilities,
    and image upload functionality of the MovieViewSet.
    Tests include permission checks for both regular users and admin users.
    """
    
    def setUp(self):
        """
        Set up test data and authentication.
        
        Creates:
        - Regular user and admin user
        - Test genres (Action, Drama)
        - Test actors (John Doe, Jane Smith)
        - Test movies with associated genres and actors
        """
        self.client = APIClient()
        
        # Create users
        self.user = get_user_model().objects.create_user(
            "test@test.com",
            "testpass123"
        )
        self.admin_user = get_user_model().objects.create_superuser(
            "admin@test.com",
            "adminpass123"
        )
        self.client.force_authenticate(self.user)
        
        # Create test data in bulk
        self.genres = {
            "action": sample_genre(name="Action"),
            "drama": sample_genre(name="Drama")
        }
        
        self.actors = {
            "john": sample_actor(first_name="John", last_name="Doe"),
            "jane": sample_actor(first_name="Jane", last_name="Smith")
        }
        
        # Create movies with relationships
        self.movies = {
            "movie1": sample_movie(
                title="Test Movie 1",
                description="Test Description 1",
                duration=120
            ),
            "movie2": sample_movie(
                title="Test Movie 2",
                description="Test Description 2",
                duration=90
            )
        }
        
        # Set up relationships
        self.movies["movie1"].genres.add(self.genres["action"])
        self.movies["movie1"].actors.add(self.actors["john"])
        
        self.movies["movie2"].genres.add(self.genres["drama"])
        self.movies["movie2"].actors.add(self.actors["jane"])

    def test_list_movies(self):
        """
        Test retrieving the list of all movies.
        
        Verifies:
        - Successful response status
        - Correct number of movies returned
        - Correct movie titles in response
        """
        res = self.client.get(MOVIE_URL)
        
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)
        self.assertEqual(res.data[0]["title"], "Test Movie 1")
        self.assertEqual(res.data[1]["title"], "Test Movie 2")

    def test_retrieve_movie(self):
        """
        Test retrieving a specific movie by ID.
        
        Verifies:
        - Successful response status
        - Correct movie details (title, description, duration)
        - Correct number of associated genres and actors
        """
        url = detail_url(self.movies["movie1"].id)
        res = self.client.get(url)
        
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["title"], "Test Movie 1")
        self.assertEqual(res.data["description"], "Test Description 1")
        self.assertEqual(res.data["duration"], 120)
        self.assertEqual(len(res.data["genres"]), 1)
        self.assertEqual(len(res.data["actors"]), 1)

    def test_create_movie_admin_only(self):
        """
        Test movie creation permissions and functionality.
        
        Verifies:
        - Regular users cannot create movies
        - Admin users can create movies
        - Created movie has correct attributes and relationships
        """
        payload = {
            "title": "New Movie",
            "description": "New Description",
            "duration": 150,
            "genres": [self.genres["action"].id],
            "actors": [self.actors["john"].id]
        }
        
        # Test with regular user
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        
        # Test with admin user
        self.client.force_authenticate(self.admin_user)
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        
        movie = Movie.objects.get(id=res.data["id"])
        self.assertEqual(movie.title, payload["title"])
        self.assertEqual(movie.description, payload["description"])
        self.assertEqual(movie.duration, payload["duration"])
        self.assertEqual(movie.genres.count(), 1)
        self.assertEqual(movie.actors.count(), 1)

    def test_filter_movies_by_title(self):
        """
        Test filtering movies by title using case-insensitive contains.
        
        Verifies:
        - Successful response status
        - Correct number of filtered movies
        - Correct movie title in filtered results
        """
        res = self.client.get(MOVIE_URL, {"title": "Movie 1"})
        
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], "Test Movie 1")

    def test_filter_movies_by_genre(self):
        """
        Test filtering movies by genre ID.
        
        Verifies:
        - Successful response status
        - Correct number of filtered movies
        - Correct movie title in filtered results
        """
        res = self.client.get(MOVIE_URL, {"genres": f"{self.genres['action'].id}"})
        
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], "Test Movie 1")

    def test_filter_movies_by_actor(self):
        """
        Test filtering movies by actor ID.
        
        Verifies:
        - Successful response status
        - Correct number of filtered movies
        - Correct movie title in filtered results
        """
        res = self.client.get(MOVIE_URL, {"actors": f"{self.actors['jane'].id}"})
        
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], "Test Movie 2")

    def test_filter_movies_by_multiple_params(self):
        """
        Test filtering movies using multiple parameters simultaneously.
        
        Verifies:
        - Successful response status
        - Correct number of filtered movies
        - Correct movie title in filtered results
        - Filtering works correctly with combined criteria
        """
        res = self.client.get(
            MOVIE_URL,
            {
                "title": "Movie",
                "genres": f"{self.genres['action'].id}",
                "actors": f"{self.actors['john'].id}"
            }
        )
        
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], "Test Movie 1")

    def test_upload_image_admin_only(self):
        """
        Test movie image upload permissions and functionality.
        
        Verifies:
        - Regular users cannot upload images
        - Admin users can upload images
        - Image is correctly saved and associated with movie
        - Image file exists in the filesystem
        """
        url = image_upload_url(self.movies["movie1"].id)
        
        # Test with regular user
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(url, {"image": ntf}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        
        # Test with admin user
        self.client.force_authenticate(self.admin_user)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(url, {"image": ntf}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)
        self.movies["movie1"].refresh_from_db()
        self.assertTrue(os.path.exists(self.movies["movie1"].image.path))

    def test_upload_invalid_image(self):
        """
        Test handling of invalid image uploads.
        
        Verifies:
        - Proper error response for invalid image data
        - Correct HTTP status code (400 Bad Request)
        """
        self.client.force_authenticate(self.admin_user)
        url = image_upload_url(self.movies["movie1"].id)
        res = self.client.post(url, {"image": "not image"}, format="multipart")
        
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
