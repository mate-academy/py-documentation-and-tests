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


MOVIES_URL = reverse("cinema:movie-list")


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


def upload_image_url(movie_id):
    return reverse("cinema:movie-upload-image", args=[movie_id])


def create_movie(**params):
    defaults = {
        "title": "Test Movie",
        "description": "Test description",
        "duration": 120,
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)


def create_user(**params):
    return get_user_model().objects.create_user(**params)


# ──────────────────────────────────────────────
# Unauthenticated access
# ──────────────────────────────────────────────

class UnauthenticatedMovieApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_auth_required_for_list(self):
        res = self.client.get(MOVIES_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


# ──────────────────────────────────────────────
# Authenticated (regular user) — read-only
# ──────────────────────────────────────────────

class AuthenticatedMovieApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(email="user@test.com", password="pass1234")
        self.client.force_authenticate(self.user)

    # ── list ──────────────────────────────────

    def test_list_movies(self):
        create_movie(title="Movie A")
        create_movie(title="Movie B")

        res = self.client.get(MOVIES_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)

    def test_list_uses_movie_list_serializer(self):
        movie = create_movie()
        res = self.client.get(MOVIES_URL)

        serializer = MovieListSerializer(movie)
        self.assertIn(serializer.data, res.data)

    # ── filters ───────────────────────────────

    def test_filter_movies_by_title(self):
        movie_a = create_movie(title="Inception")
        movie_b = create_movie(title="Interstellar")
        movie_c = create_movie(title="The Matrix")

        res = self.client.get(MOVIES_URL, {"title": "inter"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(MovieListSerializer(movie_b).data, res.data)
        self.assertNotIn(MovieListSerializer(movie_a).data, res.data)
        self.assertNotIn(MovieListSerializer(movie_c).data, res.data)

    def test_filter_movies_by_genre(self):
        genre1 = Genre.objects.create(name="Action")
        genre2 = Genre.objects.create(name="Drama")

        movie_with_genre = create_movie(title="Action Movie")
        movie_with_genre.genres.add(genre1)

        movie_without_genre = create_movie(title="Drama Movie")
        movie_without_genre.genres.add(genre2)

        res = self.client.get(MOVIES_URL, {"genres": f"{genre1.id}"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(MovieListSerializer(movie_with_genre).data, res.data)
        self.assertNotIn(MovieListSerializer(movie_without_genre).data, res.data)

    def test_filter_movies_by_actor(self):
        actor1 = Actor.objects.create(first_name="Tom", last_name="Hanks")
        actor2 = Actor.objects.create(first_name="Brad", last_name="Pitt")

        movie_with_actor = create_movie(title="Tom's Movie")
        movie_with_actor.actors.add(actor1)

        movie_without_actor = create_movie(title="Brad's Movie")
        movie_without_actor.actors.add(actor2)

        res = self.client.get(MOVIES_URL, {"actors": f"{actor1.id}"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(MovieListSerializer(movie_with_actor).data, res.data)
        self.assertNotIn(MovieListSerializer(movie_without_actor).data, res.data)

    def test_filter_by_multiple_genres(self):
        genre1 = Genre.objects.create(name="Sci-Fi")
        genre2 = Genre.objects.create(name="Thriller")
        genre3 = Genre.objects.create(name="Comedy")

        movie1 = create_movie(title="Movie 1")
        movie1.genres.add(genre1)

        movie2 = create_movie(title="Movie 2")
        movie2.genres.add(genre2)

        movie3 = create_movie(title="Movie 3")
        movie3.genres.add(genre3)

        res = self.client.get(MOVIES_URL, {"genres": f"{genre1.id},{genre2.id}"})

        self.assertIn(MovieListSerializer(movie1).data, res.data)
        self.assertIn(MovieListSerializer(movie2).data, res.data)
        self.assertNotIn(MovieListSerializer(movie3).data, res.data)

    # ── retrieve ──────────────────────────────

    def test_retrieve_movie(self):
        movie = create_movie()
        movie.genres.add(Genre.objects.create(name="Action"))

        res = self.client.get(detail_url(movie.id))

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        serializer = MovieDetailSerializer(movie)
        self.assertEqual(res.data, serializer.data)

    # ── create (forbidden for regular user) ───

    def test_create_movie_forbidden(self):
        payload = {
            "title": "New Movie",
            "description": "desc",
            "duration": 90,
        }
        res = self.client.post(MOVIES_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


# ──────────────────────────────────────────────
# Admin user — full access
# ──────────────────────────────────────────────

class AdminMovieApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = create_user(
            email="admin@test.com",
            password="adminpass",
            is_staff=True,
        )
        self.client.force_authenticate(self.admin)

    def test_create_movie(self):
        actor = Actor.objects.create(first_name="John", last_name="Doe")
        genre1 = Genre.objects.create(name="Action")
        genre2 = Genre.objects.create(name="Drama")
        payload = {
            "title": "New Movie",
            "description": "A great film",
            "duration": 130,
            "genres": [genre1.id, genre2.id],
            "actors": [actor.id],
        }
        res = self.client.post(MOVIES_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_create_movie_with_genres(self):
        genre1 = Genre.objects.create(name="Action")
        genre2 = Genre.objects.create(name="Drama")

        payload = {
            "title": "Movie with Genres",
            "description": "desc",
            "duration": 100,
            "genres": [genre1.id, genre2.id],
        }
        res = self.client.post(MOVIES_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(id=res.data["id"])
        self.assertIn(genre1, movie.genres.all())
        self.assertIn(genre2, movie.genres.all())

    def test_create_movie_with_actors(self):
        actor = Actor.objects.create(first_name="John", last_name="Doe")

        payload = {
            "title": "Movie with Actor",
            "description": "desc",
            "duration": 95,
            "actors": [actor.id],
        }
        res = self.client.post(MOVIES_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(id=res.data["id"])
        self.assertIn(actor, movie.actors.all())
