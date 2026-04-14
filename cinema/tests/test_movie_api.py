import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor
from cinema.serializers import MovieDetailSerializer, MovieListSerializer

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


class MoviePublicTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_get_movie_list_forbidden(self):
        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_movie_detail_forbidden(self):
        movie = sample_movie()

        res = self.client.get(detail_url(movie_id=movie.id))

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_post_create_movie_forbidden(self):
        res = self.client.post(
            MOVIE_URL,
            data={
                "title": "string1",
                "description": "string2",
                "duration": 45,
            }
        )

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(Movie.objects.count(), 0)


class MovieUserTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "user@test.com", "testpassword"
        )
        self.client.force_authenticate(self.user)

    def test_get_movie_list(self):
        movie = sample_movie()
        serializer = MovieListSerializer(movie)
        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer.data, res.data)

    def test_get_movies_with_title(self):
        movie_1 = sample_movie(title="WE SHOULD NOT FIND THIS FILM")
        movie_2 = sample_movie(title="TestName")

        res = self.client.get(
            MOVIE_URL,
            QUERY_STRING="title=TestName"
        )

        serializer_1 = MovieListSerializer(movie_1)
        serializer_2 = MovieListSerializer(movie_2)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertNotIn(serializer_1.data, res.data)
        self.assertIn(serializer_2.data, res.data)

    def test_get_movie_with_actor(self):
        movie_1 = sample_movie()
        movie_2 = sample_movie(title="We will find you")
        actor = sample_actor()
        movie_2.actors.add(actor)

        res = self.client.get(
            MOVIE_URL,
            QUERY_STRING=f"actors={actor.id}"
        )

        serializer_1 = MovieListSerializer(movie_1)
        serializer_2 = MovieListSerializer(movie_2)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertNotIn(serializer_1.data, res.data)
        self.assertIn(serializer_2.data, res.data)

    def test_get_movie_with_genre(self):
        movie_1 = sample_movie()
        movie_2 = sample_movie(title="We will find you")
        genre = sample_genre()
        movie_2.genres.add(genre)

        res = self.client.get(
            MOVIE_URL,
            QUERY_STRING=f"genres={genre.id}"
        )

        serializer_1 = MovieListSerializer(movie_1)
        serializer_2 = MovieListSerializer(movie_2)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertNotIn(serializer_1.data, res.data)
        self.assertIn(serializer_2.data, res.data)

    def test_get_movie_details(self):
        movie = sample_movie()
        serializer = MovieDetailSerializer(movie)
        
        res = self.client.get(
            detail_url(movie_id=movie.id)
        )
        
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(serializer.data, res.data)

    def test_post_create_movie_forbidden(self):
        res = self.client.post(
            MOVIE_URL,
            data={
                "title": "string1",
                "description": "string2",
                "duration": 45,
            }
        )

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Movie.objects.count(), 0)
