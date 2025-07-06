import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor

MOVIE_URL = reverse("cinema:movie-list")
MOVIE_SESSION_URL = reverse("cinema:moviesession-list")

User = get_user_model()


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


class MovieApiTests(TestCase):
    """Test movie API endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123"
        )
        self.admin_user = User.objects.create_superuser(
            email="admin@example.com",
            password="adminpass123"
        )
        
        self.genre1 = sample_genre(name="Action")
        self.genre2 = sample_genre(name="Comedy")
        self.actor1 = sample_actor(first_name="John", last_name="Doe")
        self.actor2 = sample_actor(first_name="Jane", last_name="Smith")
        
        self.movie1 = sample_movie(
            title="Test Movie 1",
            description="Test description 1",
            duration=120
        )
        self.movie1.genres.add(self.genre1)
        self.movie1.actors.add(self.actor1)
        
        self.movie2 = sample_movie(
            title="Test Movie 2",
            description="Test description 2",
            duration=90
        )
        self.movie2.genres.add(self.genre2)
        self.movie2.actors.add(self.actor2)
    
    def test_get_movies_list_unauthenticated(self):
        """Test retrieving movies without authentication"""
        response = self.client.get(MOVIE_URL)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertIn("title", response.data[0])
        self.assertIn("genres", response.data[0])
        self.assertIn("actors", response.data[0])
    
    def test_get_movies_list_authenticated(self):
        """Test retrieving movies with authentication"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(MOVIE_URL)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
    
    def test_get_movie_detail_unauthenticated(self):
        """Test retrieving movie detail without authentication"""
        response = self.client.get(detail_url(self.movie1.id))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], self.movie1.title)
        self.assertEqual(response.data["description"], self.movie1.description)
        self.assertEqual(response.data["duration"], self.movie1.duration)
        self.assertIn("genres", response.data)
        self.assertIn("actors", response.data)
    
    def test_get_movie_detail_authenticated(self):
        """Test retrieving movie detail with authentication"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(detail_url(self.movie1.id))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], self.movie1.title)
    
    def test_create_movie_unauthenticated(self):
        """Test creating movie without authentication"""
        payload = {
            "title": "New Movie",
            "description": "New description",
            "duration": 100,
            "genres": [self.genre1.id],
            "actors": [self.actor1.id]
        }
        
        response = self.client.post(MOVIE_URL, payload)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_create_movie_authenticated_user(self):
        """Test creating movie as authenticated regular user"""
        self.client.force_authenticate(user=self.user)
        payload = {
            "title": "New Movie",
            "description": "New description",
            "duration": 100,
            "genres": [self.genre1.id],
            "actors": [self.actor1.id]
        }
        
        response = self.client.post(MOVIE_URL, payload)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_create_movie_admin_user(self):
        """Test creating movie as admin user"""
        self.client.force_authenticate(user=self.admin_user)
        payload = {
            "title": "New Movie",
            "description": "New description",
            "duration": 100,
            "genres": [self.genre1.id],
            "actors": [self.actor1.id]
        }
        
        response = self.client.post(MOVIE_URL, payload)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["title"], payload["title"])
        self.assertEqual(response.data["description"], payload["description"])
        self.assertEqual(response.data["duration"], payload["duration"])
        
        # Check that movie was created in database
        movie = Movie.objects.get(id=response.data["id"])
        self.assertEqual(movie.title, payload["title"])
        self.assertEqual(movie.genres.count(), 1)
        self.assertEqual(movie.actors.count(), 1)
    
    def test_filter_movies_by_title(self):
        """Test filtering movies by title"""
        response = self.client.get(MOVIE_URL, {"title": "Movie 1"})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], self.movie1.title)
    
    def test_filter_movies_by_title_case_insensitive(self):
        """Test filtering movies by title is case insensitive"""
        response = self.client.get(MOVIE_URL, {"title": "movie 1"})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], self.movie1.title)
    
    def test_filter_movies_by_genre(self):
        """Test filtering movies by genre"""
        response = self.client.get(MOVIE_URL, {"genres": str(self.genre1.id)})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], self.movie1.title)
    
    def test_filter_movies_by_multiple_genres(self):
        """Test filtering movies by multiple genres"""
        response = self.client.get(
            MOVIE_URL, 
            {"genres": f"{self.genre1.id},{self.genre2.id}"}
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
    
    def test_filter_movies_by_actor(self):
        """Test filtering movies by actor"""
        response = self.client.get(MOVIE_URL, {"actors": str(self.actor1.id)})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], self.movie1.title)
    
    def test_filter_movies_by_multiple_actors(self):
        """Test filtering movies by multiple actors"""
        response = self.client.get(
            MOVIE_URL, 
            {"actors": f"{self.actor1.id},{self.actor2.id}"}
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
    
    def test_filter_movies_combined_filters(self):
        """Test filtering movies with multiple filters"""
        response = self.client.get(MOVIE_URL, {
            "title": "Movie 1",
            "genres": str(self.genre1.id),
            "actors": str(self.actor1.id)
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], self.movie1.title)
    
    def test_filter_movies_no_results(self):
        """Test filtering movies with no matching results"""
        response = self.client.get(MOVIE_URL, {"title": "Non-existent Movie"})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)
    
    def test_invalid_movie_id(self):
        """Test retrieving movie with invalid ID"""
        response = self.client.get(detail_url(999))
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_create_movie_invalid_data(self):
        """Test creating movie with invalid data"""
        self.client.force_authenticate(user=self.admin_user)
        payload = {
            "title": "",  # Empty title
            "description": "Test description",
            "duration": -10,  # Negative duration
        }
        
        response = self.client.post(MOVIE_URL, payload)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_create_movie_missing_required_fields(self):
        """Test creating movie with missing required fields"""
        self.client.force_authenticate(user=self.admin_user)
        payload = {
            "title": "Test Movie",
            # Missing description and duration
        }
        
        response = self.client.post(MOVIE_URL, payload)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


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
