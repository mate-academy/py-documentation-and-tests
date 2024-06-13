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


class UnauthenticatedMovieApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEquals(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com",
            password="testpassword"
        )
        self.client.force_authenticate(self.user)

    def test_movie_list(self):
        sample_movie()
        movie_with_genres_and_actors = sample_movie()

        genre = Genre.objects.create(name="drama")
        actor = Actor.objects.create(first_name="Dram", last_name="King")

        movie_with_genres_and_actors.genres.add(genre)
        movie_with_genres_and_actors.actors.add(actor)

        res = self.client.get(MOVIE_URL)

        movies = Movie.objects.all()

        serializer = MovieListSerializer(movies, many=True)

        self.assertEquals(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_title(self):

        movie_1 = sample_movie(title="Absolute film")
        movie_2 = sample_movie(title="B films test")
        movie_3 = sample_movie(title="None movie")

        res = self.client.get(
            MOVIE_URL,
            {
                "title": "movie"
            }
        )

        serializer_movie_1 = MovieListSerializer(movie_1)
        serializer_movie_2 = MovieListSerializer(movie_2)
        serializer_movie_3 = MovieListSerializer(movie_3)

        self.assertNotIn(serializer_movie_1.data, res.data)
        self.assertNotIn(serializer_movie_2.data, res.data)
        self.assertIn(serializer_movie_3.data, res.data)

    def test_filter_movies_by_genres(self):

        movie_1 = sample_movie()
        movie_2 = sample_movie()
        movie_3 = sample_movie()

        genre_1 = Genre.objects.create(name="Genre-1")
        genre_2 = Genre.objects.create(name="Genre-2")
        genre_3 = Genre.objects.create(name="Genre-3")

        movie_1.genres.add(genre_1)
        movie_2.genres.add(genre_1)
        movie_2.genres.add(genre_2)
        movie_3.genres.add(genre_1)
        movie_3.genres.add(genre_2)
        movie_3.genres.add(genre_3)

        res = self.client.get(
            MOVIE_URL,
            {
                "genres": f"{genre_2.id}"
            }
        )

        serializer_movie_1 = MovieListSerializer(movie_1)
        serializer_movie_2 = MovieListSerializer(movie_2)
        serializer_movie_3 = MovieListSerializer(movie_3)

        self.assertNotIn(serializer_movie_1.data, res.data)
        self.assertIn(serializer_movie_2.data, res.data)
        self.assertIn(serializer_movie_3.data, res.data)

    def test_filter_movies_by_actors(self):
        movie_1 = sample_movie()
        movie_2 = sample_movie()
        movie_3 = sample_movie()

        actor_1 = Actor.objects.create(first_name="Actor", last_name="1")
        actor_2 = Actor.objects.create(first_name="Actor", last_name="2")
        actor_3 = Actor.objects.create(first_name="Actor", last_name="3")

        movie_1.actors.add(actor_1)
        movie_2.actors.add(actor_1)
        movie_2.actors.add(actor_2)
        movie_3.actors.add(actor_1)
        movie_3.actors.add(actor_2)
        movie_3.actors.add(actor_3)

        res = self.client.get(
            MOVIE_URL,
            {
                "actors": f"{actor_2.id}"
            }
        )

        serializer_movie_1 = MovieListSerializer(movie_1)
        serializer_movie_2 = MovieListSerializer(movie_2)
        serializer_movie_3 = MovieListSerializer(movie_3)

        self.assertNotIn(serializer_movie_1.data, res.data)
        self.assertIn(serializer_movie_2.data, res.data)
        self.assertIn(serializer_movie_3.data, res.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        movie.genres.add(Genre.objects.create(name="TestGenre"))

        url = detail_url(movie.id)

        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEquals(res.status_code, status.HTTP_200_OK)
        self.assertEquals(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "TEST_TITLE"
        }
        res = self.client.post(MOVIE_URL, payload)

        self.assertEquals(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@test.test",
            password="adminpassword",
            is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_movie_admin(self):
        genre_1 = Genre.objects.create(name="GENRE-1")
        actor_1 = Actor.objects.create(first_name="Actor", last_name="1")
        payload = {
            "title": "New Test Movie",
            "description": "Description for the new movie",
            "duration": 120,
            "genres": [genre_1.id],
            "actors": [actor_1.id],
        }

        response = self.client.post(reverse("cinema:movie-list"), payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_delete_movie_not_allowed(self):

        movie = sample_movie()

        url = detail_url(movie.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
