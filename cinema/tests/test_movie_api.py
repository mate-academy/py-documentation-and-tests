import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

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
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)

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
            res = self.client.post(
                url,
                data={"image": ntf},
                format="multipart",
                HTTP_AUTHORIZATION=f"Bearer {self.access_token}"
            )
        self.movie.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)
        self.assertTrue(os.path.exists(self.movie.image.path))

    def test_upload_image_bad_request(self):
        """Test uploading an invalid image"""
        url = image_upload_url(self.movie.id)
        res = self.client.post(
            url,
            data={"image": "not image"},
            format="multipart",
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}"
        )

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_image_to_movie_list(self):
        url = MOVIE_URL
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(
                url,
                data={
                    "title": "Title",
                    "description": "Description",
                    "duration": 90,
                    "genres": [1],
                    "actors": [1],
                    "image": ntf,
                },
                format="multipart",
                HTTP_AUTHORIZATION=f"Bearer {self.access_token}"
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
            self.client.post(
                url,
                data={"image": ntf},
                format="multipart",
                HTTP_AUTHORIZATION=f"Bearer {self.access_token}"
            )
        res = self.client.get(
            detail_url(self.movie.id),
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}"
        )

        self.assertIn("image", res.data)

    def test_image_url_is_shown_on_movie_list(self):
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(
                url,
                data={"image": ntf},
                format="multipart",
                HTTP_AUTHORIZATION=f"Bearer {self.access_token}"
            )
        res = self.client.get(
            MOVIE_URL,
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}"
        )

        self.assertIn("image", res.data[0].keys())

    def test_image_url_is_shown_on_movie_session_detail(self):
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(
                url,
                data={"image": ntf},
                format="multipart",
                HTTP_AUTHORIZATION=f"Bearer {self.access_token}"
            )
        res = self.client.get(
            MOVIE_SESSION_URL,
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}"
        )

        self.assertIn("movie_image", res.data[0].keys())


class MovieViewUnauthenticatedTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_list_auth_required(self):
        res = self.client.get(reverse("cinema:movie-list"))
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class MovieViewAuthenticatedTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@gmail.com",
            password="test_password",
        )
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)

    def test_movie_upload_authenticated(self):
        movie_info = {
            "title": "Sample movie",
            "description": "Sample description",
            "duration": 90,
            "genres": [sample_genre().id],
            "actors": [sample_actor().id],
        }

        res = self.client.post(
            reverse("cinema:movie-list"),
            data=movie_info,
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}"
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Movie.objects.filter(title=movie_info["title"]).exists())

    def test_movie_list_authenticated(self):
        sample_movie()
        movie_with_actors_and_genres = sample_movie()
        movie_with_actors_and_genres.actors.add(sample_actor())
        movie_with_actors_and_genres.genres.add(sample_genre())
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        res = self.client.get(
            reverse("cinema:movie-list"),
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}"
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_movie_detail_authenticated(self):
        movie = sample_movie()
        serializer = MovieDetailSerializer(movie)

        res = self.client.get(
            reverse("cinema:movie-detail", args=[movie.id]),
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}"
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_movie_update_authenticated(self):
        movie = sample_movie()
        data = {"title": "Changed"}
        res = self.client.put(
            reverse("cinema:movie-detail", args=[movie.id]),
            data,
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}"
        )
        self.assertEqual(res.status_code, 403)

    def test_movie_delete_authenticated(self):
        movie = sample_movie()
        res = self.client.delete(
            reverse("cinema:movie-detail", args=[movie.id]),
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}"
        )
        self.assertEqual(res.status_code, 403)

    def test_filter_movies_by_title(self):
        movie1 = sample_movie(title="Sample movie")
        movie2 = sample_movie(title="qwerty")
        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)

        res = self.client.get(
            reverse("cinema:movie-list"),
            data={"title": "sample"},
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}"
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

    def test_filter_movies_by_genres(self):
        genre1 = sample_genre(name="Drama")
        genre2 = sample_genre(name="Sci-fi")
        movie1 = sample_movie(title="Sample movie1")
        movie2 = sample_movie(title="Sample movie2")
        movie1.genres.add(genre1)
        movie2.genres.add(genre2)
        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)

        res = self.client.get(
            reverse("cinema:movie-list"),
            data={"genres": str(genre1.id)},
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}"
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

    def test_filter_movies_by_actors(self):
        actor1 = sample_actor(first_name="John")
        actor2 = sample_actor(first_name="Carl")
        movie1 = sample_movie(title="Sample movie1")
        movie2 = sample_movie(title="Sample movie2")
        movie1.actors.add(actor1)
        movie2.actors.add(actor2)
        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)

        res = self.client.get(
            reverse("cinema:movie-list"),
            data={"actors": str(actor1.id)},
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}"
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)


class MovieViewAdminTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            email="admin@gmail.com",
            password="admin_password",
        )
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)

    def test_movie_upload_admin(self):
        movie_info = {
            "title": "Sample movie",
            "description": "Sample description",
            "duration": 90,
            "genres": [sample_genre().id],
            "actors": [sample_actor().id],
        }

        res = self.client.post(
            reverse("cinema:movie-list"),
            data=movie_info,
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}"
        )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Movie.objects.filter(title=movie_info["title"]).exists())


