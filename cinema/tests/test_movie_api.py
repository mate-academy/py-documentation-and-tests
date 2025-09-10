import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.test.utils import override_settings

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

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
    """Test unauthenticated movie API access"""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test that authentication is required"""
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    """Test authenticated movie API access"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="test@test.com", password="testpass123"
        )
        self.client.force_authenticate(self.user)

    def test_movies_list(self):
        """Test retrieving movies list"""
        sample_movie()
        movie_with_relations = sample_movie(title="Second Movie")

        genre = sample_genre()
        actor = sample_actor()

        movie_with_relations.genres.add(genre)
        movie_with_relations.actors.add(actor)

        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_title(self):
        """Test filtering movies by title"""
        movie1 = sample_movie(title="Avatar")
        movie2 = sample_movie(title="Titanic")
        movie3 = sample_movie(title="Avatar 2")

        res = self.client.get(MOVIE_URL, {"title": "Avatar"})

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie3)

        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)
        self.assertIn(serializer3.data, res.data)

    def test_filter_movies_by_genres(self):
        """Test filtering movies by genres"""
        movie1 = sample_movie(title="Drama Movie")
        movie2 = sample_movie(title="Action Movie")
        movie3 = sample_movie(title="Mixed Movie")

        genre1 = sample_genre(name="Drama")
        genre2 = sample_genre(name="Action")

        movie1.genres.add(genre1)
        movie2.genres.add(genre2)
        movie3.genres.add(genre1, genre2)

        res = self.client.get(MOVIE_URL, {"genres": f"{genre1.id}"})

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie3)

        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)
        self.assertIn(serializer3.data, res.data)

    def test_filter_movies_by_multiple_genres(self):
        """Test filtering movies by multiple genres"""
        movie1 = sample_movie(title="Drama Movie")
        movie2 = sample_movie(title="Action Movie")
        movie3 = sample_movie(title="Drama Action Movie")

        genre1 = sample_genre(name="Drama")
        genre2 = sample_genre(name="Action")

        movie1.genres.add(genre1)
        movie2.genres.add(genre2)
        movie3.genres.add(genre1, genre2)

        res = self.client.get(MOVIE_URL, {"genres": f"{genre1.id},{genre2.id}"})

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie3)

        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertIn(serializer3.data, res.data)

    def test_filter_movies_by_actors(self):
        """Test filtering movies by actors"""
        movie1 = sample_movie(title="Movie with Actor 1")
        movie2 = sample_movie(title="Movie with Actor 2")
        movie3 = sample_movie(title="Movie with both actors")

        actor1 = sample_actor(first_name="John", last_name="Doe")
        actor2 = sample_actor(first_name="Jane", last_name="Smith")

        movie1.actors.add(actor1)
        movie2.actors.add(actor2)
        movie3.actors.add(actor1, actor2)

        res = self.client.get(MOVIE_URL, {"actors": f"{actor1.id}"})

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie3)

        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)
        self.assertIn(serializer3.data, res.data)

    def test_retrieve_movie_detail(self):
        """Test retrieving movie detail"""
        movie = sample_movie()
        movie.genres.add(sample_genre())
        movie.actors.add(sample_actor())

        url = detail_url(movie.id)
        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        """Test that regular users cannot create movies"""
        payload = {
            "title": "New Movie",
            "description": "New description",
            "duration": 90,
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_upload_image_forbidden(self):
        """Test that regular users cannot upload movie images"""
        movie = sample_movie()
        url = image_upload_url(movie.id)

        with tempfile.NamedTemporaryFile(suffix=".jpg") as image_file:
            img = Image.new("RGB", (10, 10))
            img.save(image_file, format="JPEG")
            image_file.seek(0)

            payload = {"image": image_file}
            res = self.client.post(url, payload, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_movie_forbidden(self):
        """Test that regular users cannot update movies"""
        movie = sample_movie()
        url = detail_url(movie.id)

        res = self.client.patch(url, {"title": "New Title"})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_movie_forbidden(self):
        """Test that regular users cannot delete movies"""
        movie = sample_movie()
        url = detail_url(movie.id)

        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTests(TestCase):
    """Test admin movie API access"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="admin@admin.com", password="testpass123", is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        """Test creating movie"""
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
        movie = Movie.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        # Проверяем только основные поля, не ManyToMany
        self.assertEqual(payload["title"], movie.title)
        self.assertEqual(payload["description"], movie.description)
        self.assertEqual(payload["duration"], movie.duration)

    def test_create_movie_with_genres_and_actors(self):
        """Test creating movie with genres and actors"""
        genre1 = sample_genre(name="Action")
        genre2 = sample_genre(name="Drama")
        actor1 = sample_actor(first_name="John", last_name="Doe")
        actor2 = sample_actor(first_name="Jane", last_name="Smith")

        payload = {
            "title": "New Movie",
            "description": "New description",
            "duration": 90,
            "genres": [genre1.id, genre2.id],
            "actors": [actor1.id, actor2.id],
        }

        res = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=res.data["id"])
        genres = movie.genres.all()
        actors = movie.actors.all()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn(genre1, genres)
        self.assertIn(genre2, genres)
        self.assertIn(actor1, actors)
        self.assertIn(actor2, actors)
        self.assertEqual(genres.count(), 2)
        self.assertEqual(actors.count(), 2)

    def test_upload_image(self):
        """Test uploading image to movie"""
        movie = sample_movie()
        url = image_upload_url(movie.id)

        with tempfile.NamedTemporaryFile(suffix=".jpg") as image_file:
            img = Image.new("RGB", (10, 10))
            img.save(image_file, format="JPEG")
            image_file.seek(0)

            payload = {"image": image_file}
            res = self.client.post(url, payload, format="multipart")

        movie.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)
        self.assertTrue(os.path.exists(movie.image.path))

    def test_update_movie(self):
        """Test updating movie (PATCH)"""
        movie = sample_movie()
        genre = sample_genre()

        url = detail_url(movie.id)
        payload = {"title": "Updated Title"}

        res = self.client.patch(url, payload)
        movie.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(movie.title, payload["title"])

    def test_delete_movie(self):
        """Test deleting movie"""
        movie = sample_movie()
        url = detail_url(movie.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Movie.objects.filter(id=movie.id).exists())

    def tearDown(self):
        """Clean up uploaded images after tests"""
        for movie in Movie.objects.all():
            if movie.image:
                if os.path.exists(movie.image.path):
                    os.remove(movie.image.path)


class JWTAuthenticationTests(TestCase):
    """Test JWT authentication via Authorization headers"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="test@test.com", password="testpass123"
        )

    def test_get_jwt_token(self):
        """Test obtaining JWT token"""
        url = reverse("user:token_obtain_pair")
        res = self.client.post(
            url, {"email": "test@test.com", "password": "testpass123"}
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("access", res.data)

    def test_access_with_jwt_token(self):
        """Test accessing protected endpoint with JWT token"""
        token_url = reverse("user:token_obtain_pair")
        token_res = self.client.post(
            token_url, {"email": "test@test.com", "password": "testpass123"}
        )
        token = token_res.data["access"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)


class ThrottlingConfigTests(TestCase):
    """Test throttling configuration"""

    def test_throttling_classes_configured(self):
        """Test that throttling classes are configured"""
        from django.conf import settings
        throttle_classes = settings.REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES']

        self.assertIn('rest_framework.throttling.AnonRateThrottle', throttle_classes)
        self.assertIn('rest_framework.throttling.UserRateThrottle', throttle_classes)

    def test_throttling_rates_configured(self):
        """Test that throttling rates are configured"""
        from django.conf import settings
        throttle_rates = settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']

        self.assertEqual(throttle_rates['anon'], '10/minute')
        self.assertEqual(throttle_rates['user'], '30/minute')
