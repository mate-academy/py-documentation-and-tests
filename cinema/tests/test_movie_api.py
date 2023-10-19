import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor
from cinema.serializers import MovieSerializer, MovieDetailSerializer, MovieListSerializer

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


class UnauthenticatedMovieViewTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthorizedMovieSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser("admin@myproject.com", "password")
        self.client.force_authenticate(self.user)
        self.actors = [
            sample_actor(first_name=f"First_name {i}", last_name=f"Last_name {i}")
            for i in range(2)
        ]
        self.genres = [sample_genre(name=f"Genre {i}") for i in range(2)]
        self.movie_1 = sample_movie(title="Movie 1")
        self.movie_1.genres.add(self.genres[0])
        self.movie_1.actors.add(self.actors[0])
        self.movie_2 = sample_movie(title="Movie 2")
        self.movie_2.genres.add(self.genres[1])
        self.movie_2.actors.add(self.actors[1])

    def test_genres_filter(self):
        res = self.client.get(MOVIE_URL, {"genres": f"{self.genres[0].id}"})
        serializer_1 = MovieListSerializer(self.movie_1)
        serializer_2 = MovieListSerializer(self.movie_2)
        self.assertIn(serializer_1.data, res.data)
        self.assertNotIn(serializer_2.data, res.data)

    def test_actors_filter(self):
        res = self.client.get(MOVIE_URL, {"actors": f"{self.actors[0].id}"})
        serializer_1 = MovieListSerializer(self.movie_1)
        serializer_2 = MovieListSerializer(self.movie_2)
        self.assertIn(serializer_1.data, res.data)
        self.assertNotIn(serializer_2.data, res.data)

    def test_title_filter(self):
        res = self.client.get(MOVIE_URL, {"title": f"{self.movie_1.title}"})
        serializer_1 = MovieListSerializer(self.movie_1)
        serializer_2 = MovieListSerializer(self.movie_2)
        self.assertIn(serializer_1.data, res.data)
        self.assertNotIn(serializer_2.data, res.data)

    def test_movie_list(self):
        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_movie_detail(self):
        res = self.client.get(reverse("cinema:movie-detail", args=[1]))
        serializer = MovieDetailSerializer(self.movie_1)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)


class MovieSessionTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser("admin@myproject.com", "password")
        self.client.force_authenticate(self.user)
        self.movie_1 = sample_movie(title="movie with id 0")
        self.movie_2 = sample_movie(title="movie with id 1")

    def test_movie_filter(self):
        sample_movie_session(movie=self.movie_1)
        sample_movie_session(movie=self.movie_2)
        res = self.client.get(MOVIE_SESSION_URL, {"movie": self.movie_1.id})
        self.assertIn(self.movie_1.title, str(res.data[0]))
        self.assertNotIn(self.movie_2.title, str(res.data[0]))

    def test_date_filter(self):
        sample_movie_session(movie=self.movie_1, show_time="2022-11-11")
        sample_movie_session(movie=self.movie_2, show_time="2021-12-25")
        res = self.client.get(MOVIE_SESSION_URL, {"date": "2022-11-11"})
        self.assertIn(self.movie_1.title, str(res.data[0]))
        self.assertNotIn(self.movie_2.title, str(res.data[0]))


class AdminMovieTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user("admin@admin.com", "password", is_staff=True)
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        genre = sample_genre()
        actor = sample_actor()
        movie_data = {
            "title": "test_title",
            "description": "test_description",
            "duration": 256,
            "actors": actor.id,
            "genres": genre.id,
        }
        res = self.client.post(MOVIE_URL, movie_data)
        movie = Movie.objects.get(id=1)
        serializer = MovieSerializer(movie)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data, serializer.data)

    def test_delete_forbidden(self):
        movie = sample_movie()
        res = self.client.delete(reverse("cinema:movie-detail", args=[movie.id]))
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
