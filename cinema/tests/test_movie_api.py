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
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create(
            email="testmail@test.test", password="testpassword"
        )
        self.client.force_authenticate(self.user)

    def test_movie_list(self):
        sample_movie()

        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.data, serializer.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_movie_filter_by_title(self):
        sample_movie()
        sample_movie(
            title="Nemo",
            description="Fun cartoon",
            duration=90
        )

        res = self.client.get(
            MOVIE_URL, {"title": "nemo"}
        )
        movies = Movie.objects.filter(title__icontains="nem")
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.data, serializer.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_movie_filter_by_genres(self):
        movie_without_genre = sample_movie()
        movie_with_genre1 = sample_movie()
        movie_with_genre2 = sample_movie()

        test_genre1 = sample_genre(name="horror")
        test_genre2 = sample_genre(name="Sci-fi")

        movie_with_genre1.genres.add(test_genre1)
        movie_with_genre2.genres.add(test_genre2)

        res = self.client.get(
            MOVIE_URL,
            {"genres": f"{test_genre1.id},{test_genre2.id}"}
        )

        serializer_without_genre = MovieListSerializer(movie_without_genre)
        serializer_with_genre1 = MovieListSerializer(movie_with_genre1)
        serializer_with_genre2 = MovieListSerializer(movie_with_genre2)

        self.assertIn(serializer_with_genre1.data, res.data)
        self.assertIn(serializer_with_genre2.data, res.data)
        self.assertNotIn(serializer_without_genre.data, res.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_movie_filter_by_actors(self):
        movie_without_actors = sample_movie()
        movie_with_actor1 = sample_movie()
        movie_with_actor2 = sample_movie()

        test_actor1 = sample_actor(first_name="Oleg", last_name="Ol")
        test_actor2 = sample_actor(first_name="Sava", last_name="Lol")

        movie_with_actor1.actors.add(test_actor1)
        movie_with_actor2.actors.add(test_actor2)

        res = self.client.get(
            MOVIE_URL,
            {"actors": f"{test_actor1.id},{test_actor2.id}"}
        )

        serializer_without_actors = MovieListSerializer(movie_without_actors)
        serializer_with_actor1 = MovieListSerializer(movie_with_actor1)
        serializer_with_actor2 = MovieListSerializer(movie_with_actor2)

        self.assertIn(serializer_with_actor1.data, res.data)
        self.assertIn(serializer_with_actor2.data, res.data)
        self.assertNotIn(serializer_without_actors.data, res.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        movie.genres.add(
            Genre.objects.create(name="test genre")
        )
        movie.actors.add(
            Actor.objects.create(first_name="Test name", last_name="Test last name")
        )

        url = detail_url(movie.id)
        res = self.client.get(url)
        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Test movie",
            "description": "Test description",
            "duration": 90,
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = get_user_model().objects.create_superuser(
            email="admin@test.ua",
            password="testpass"
        )
        self.client.force_authenticate(self.admin)

    def test_create_movie(self):
        payload = {
            "title": "Test movie",
            "description": "Test description",
            "duration": 90,
        }

        res = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_create_movie_with_actors_and_genres(self):
        test_actor1 = sample_actor(first_name="Oleg", last_name="Ol")
        test_actor2 = sample_actor(first_name="Sava", last_name="Lol")

        test_genre1 = sample_genre(name="horror")
        test_genre2 = sample_genre(name="Sci-fi")

        payload = {
            "title": "Test movie",
            "description": "Test description",
            "duration": 90,
            "genres": [test_genre1.id, test_genre2.id],
            "actors": [test_actor1.id, test_actor2.id]
        }
        res = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=res.data["id"])
        genres = movie.genres.all()
        actors = movie.actors.all()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn(test_actor1, actors)
        self.assertIn(test_actor2, actors)
        self.assertIn(test_genre1, genres)
        self.assertIn(test_genre2, genres)
        self.assertEqual(genres.count(), 2)
        self.assertEqual(actors.count(), 2)

    def test_delete_movie_not_allowed(self):
        movie = sample_movie()

        url = detail_url(movie.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
