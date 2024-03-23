import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor
from cinema.serializers import MovieListSerializer

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
        self.movie = sample_movie()

    def test_movie_list_unauthorized(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_movie_retrieve_unauthorized(self):
        res = self.client.get(
            reverse("cinema:movie-detail", args=(self.movie.id,))
        )
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_movie_create_unauthorized(self):
        res = self.client.post(
            data={
                "title": "Test movie",
                "duration": 100,
                "description": "Some test movie",
            },
            path=MOVIE_URL
        )

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)
        self.movie = sample_movie()
        for i in range(5):
            sample_movie(
                title=f"Movie {i}",
            )

    def test_movie_list_with_genres(self):
        movie_with_genres_filter = sample_movie(title="Movie 3")

        genre_1 = sample_genre(name="Comedy")
        genre_2 = sample_genre(name="Drama")

        movie_with_genres_filter.genres.set([genre_1, genre_2])

        res = self.client.get(
            MOVIE_URL,
            {
                "genres": f"{genre_1.id},{genre_2.id}",
                "title": "Movie"
            }
        )
        serializer_movie_without_genres = MovieListSerializer(self.movie)
        serializer_movie_with_genres = MovieListSerializer(movie_with_genres_filter)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer_movie_with_genres.data, res.data)
        self.assertNotIn(serializer_movie_without_genres, res.data)

    def test_movie_list_actors(self):
        movie_with_actors_filter = sample_movie(title="Movie 2")

        actor_1 = sample_actor(last_name="Smith")
        actor_2 = sample_actor(last_name="Black")

        movie_with_actors_filter.actors.set([actor_1, actor_2])

        res = self.client.get(
            MOVIE_URL,
            {
                "actors": f"{actor_1.id},{actor_2.id}",
                "title": "Movie"
            }
        )
        serializer_movie_without_actors = MovieListSerializer(self.movie)
        serializer_movie_with_actors = MovieListSerializer(movie_with_actors_filter)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer_movie_with_actors.data, res.data)
        self.assertNotIn(serializer_movie_without_actors, res.data)

    def test_movie_create_forbidden(self):
        res = self.client.post(
            data={
                "title": "Test movie",
                "duration": 100,
                "description": "Some test movie",
            },
            path=MOVIE_URL
        )

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_movie_retrieve(self):
        res = self.client.get(
            reverse("cinema:movie-detail", args=(self.movie.id,))
        )
        movie = Movie.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["title"], movie.title)


class AdminMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)
        self.movie = sample_movie()
        self.genre = sample_genre()
        self.actor = sample_actor()
        for i in range(5):
            sample_movie(
                title=f"Movie {i}",
            )

    def test_movie_create(self):
        payload = {
            "title": "Test movie",
            "duration": 100,
            "description": "Some test movie",
            "genres": (self.genre.id,),
            "actors": (self.actor.id,)
        }
        res = self.client.post(
            MOVIE_URL,
            payload
        )

        movie = Movie.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        payload.pop("genres")
        payload.pop("actors")
        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_movie_patch_not_allowed(self):
        payload = {
            "title": "Updated title"
        }
        res = self.client.patch(
            reverse("cinema:movie-detail", args=(self.movie.id,)),
            payload
        )

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
