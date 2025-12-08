import os
import tempfile

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import (
    Movie,
    MovieSession,
    CinemaHall,
    Genre,
    Actor
)
from cinema.serializers import (
    MovieDetailSerializer,
    MovieListSerializer
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
    genre, _ = Genre.objects.get_or_create(**defaults)

    return genre


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


class MovieViewSetUnauthenticatedTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.movie = sample_movie()
        self.valid_payload = {
            "title": "New Movie",
            "description": "New Description",
            "duration": 120,
            "genres": [1],
            "actors": [1]
        }

    def test_auth_required(self):
        """Test that authentication is required"""
        url = MOVIE_URL
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_movie(self):
        url = detail_url(self.movie.id)
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_movie_unauthorized(self):
        """Test that creating a movie is not allowed for unauthenticated users"""
        res = self.client.post(MOVIE_URL, self.valid_payload)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_movie_unauthorized(self):
        """Test that updating a movie is not allowed for unauthenticated users"""
        payload = {"title": "Updated Title"}
        url = detail_url(self.movie.id)
        res = self.client.patch(url, payload)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_movie_unauthorized(self):
        """Test that deleting a movie is not allowed for unauthenticated users"""
        url = detail_url(self.movie.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class MovieViewSetAuthorizedTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "user@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)
        self.movie = sample_movie()
        self.valid_payload = {
            "title": "New Movie",
            "description": "New Description",
            "duration": 120,
            "genres": [1],
            "actors": [1]
        }

    def test_retrieve_movie(self):
        url = detail_url(self.movie.id)
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, MovieDetailSerializer(self.movie).data)

    def test_list_movies(self):
        url = MOVIE_URL
        res = self.client.get(url)
        movies = Movie.objects.all().order_by("-id")
        serializer = MovieListSerializer(movies, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)
    
    def test_filter_movies_by_title(self):
        """Test filtering movies by title"""
        movie1 = sample_movie(title="The Dark Knight")
        movie2 = sample_movie(title="Inception")
        movie3 = sample_movie(title="The Dark Knight Rises")
        
        res = self.client.get(MOVIE_URL, {"title": "dark"})
        
        serializer1 = MovieListSerializer(movie1)
        serializer3 = MovieListSerializer(movie3)
        
        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer3.data, res.data)
        self.assertEqual(len(res.data), 2)
    
    def test_filter_movies_by_genres(self):
        """Test filtering movies by genre ids"""
        genre1 = sample_genre(name="Action")
        genre2 = sample_genre(name="Drama")
        
        movie1 = sample_movie(title="Action Movie")
        movie1.genres.add(genre1)
        
        movie2 = sample_movie(title="Drama Movie")
        movie2.genres.add(genre2)
        
        movie3 = sample_movie(title="Action Drama")
        movie3.genres.add(genre1, genre2)
        
        res = self.client.get(MOVIE_URL, {"genres": f"{genre1.id}"})
        
        serializer1 = MovieListSerializer(movie1)
        serializer3 = MovieListSerializer(movie3)
        
        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer3.data, res.data)
        self.assertEqual(len(res.data), 2)
    
    def test_filter_movies_by_actors(self):
        """Test filtering movies by actor ids"""
        actor1 = sample_actor(first_name="Leonardo", last_name="DiCaprio")
        actor2 = sample_actor(first_name="Tom", last_name="Hanks")
        
        movie1 = sample_movie(title="Movie 1")
        movie1.actors.add(actor1)
        
        movie2 = sample_movie(title="Movie 2")
        movie2.actors.add(actor2)
        
        movie3 = sample_movie(title="Movie 3")
        movie3.actors.add(actor1, actor2)
        
        res = self.client.get(MOVIE_URL, {"actors": f"{actor1.id}"})
        
        serializer1 = MovieListSerializer(movie1)
        serializer3 = MovieListSerializer(movie3)
        
        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer3.data, res.data)
        self.assertEqual(len(res.data), 2)
    
    def test_filter_movies_by_combined_filters(self):
        """Test filtering movies by multiple filters"""
        action = sample_genre(name="Action")
        drama = sample_genre(name="Drama")
        
        actor1 = sample_actor(first_name="Christian", last_name="Bale")
        actor2 = sample_actor(first_name="Heath", last_name="Ledger")
        
        movie1 = sample_movie(title="The Dark Knight")
        movie1.genres.add(action, drama)
        movie1.actors.add(actor1, actor2)
        
        movie2 = sample_movie(title="Inception")
        movie2.genres.add(action)
        movie2.actors.add(actor1)
        
        movie3 = sample_movie(title="The Prestige")
        movie3.genres.add(drama)
        movie3.actors.add(actor1)
        
        res = self.client.get(MOVIE_URL, {
            "title": "dark",
            "genres": f"{action.id}"
        })
        
        serializer1 = MovieListSerializer(movie1)
        self.assertIn(serializer1.data, res.data)
        self.assertEqual(len(res.data), 1)
        
        res = self.client.get(MOVIE_URL, {
            "genres": f"{drama.id}",
            "actors": f"{actor2.id}"
        })
        
        self.assertIn(serializer1.data, res.data)
        self.assertEqual(len(res.data), 1)

    def __test_create_movie_forbidden(self):
        """Test that creating a movie is not allowed for non-admin users"""
        res = self.client.post(MOVIE_URL, self.valid_payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def __test_update_movie_forbidden(self):
        """Test that updating a movie is not allowed for non-admin users"""
        payload = {"title": "Updated Title"}
        url = detail_url(self.movie.id)
        res = self.client.patch(url, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def __test_delete_movie_forbidden(self):
        """Test that deleting a movie is not allowed for non-admin users"""
        url = detail_url(self.movie.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class MovieViewSetAdminTests(MovieViewSetAuthorizedTests):
    def setUp(self):
        self.client = APIClient()
        self.admin = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(self.admin)
        self.movie = sample_movie()
        self.genre = sample_genre()
        self.actor = sample_actor()
        self.valid_payload = {
            "title": "New Movie",
            "description": "New Description",
            "duration": 120,
            "genres": [1],
            "actors": [1]
        }

    def test_create_movie(self):
        """Test creating a movie"""
        res = self.client.post(MOVIE_URL, self.valid_payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(id=res.data["id"])
        self.assertEqual(movie.title, self.valid_payload["title"])
        self.assertEqual(movie.duration, self.valid_payload["duration"])

    def test_retrieve_movie(self):
        url = detail_url(self.movie.id)
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, MovieDetailSerializer(self.movie).data)

    def test_list_movies(self):
        url = MOVIE_URL
        res = self.client.get(url)
        movies = Movie.objects.all().order_by("-id")
        serializer = MovieListSerializer(movies, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)
