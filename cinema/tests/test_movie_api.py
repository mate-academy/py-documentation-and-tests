import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient, APITestCase
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer, MovieSerializer

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


MOVIE_LIST_URL = reverse("cinema:movie-list")


class UnauthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_unauthenticated_movie_api(self):
        res = self.client.get(MOVIE_LIST_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="testemail@test.com",
            password="testPass"
        )
        self.client.force_authenticate(self.user)
        self.actor1 = sample_actor(first_name="test1", last_name="Test")
        self.actor2 = sample_actor(first_name="test2", last_name="Test")
        self.genre1 = sample_genre(name="test1")
        self.genre2 = sample_genre(name="test2")
        self.movie1 = sample_movie(
            title="test1",
            description="test 1")
        self.movie2 = sample_movie(
            title="test2",
            description="test 2"
        )
        self.movie1.actors.add(self.actor1)
        self.movie2.actors.add(self.actor2)
        self.movie1.genres.add(self.genre1)
        self.movie2.genres.add(self.genre2)

    def test_list_movies(self):
        res = self.client.get(MOVIE_LIST_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_list_movies_with_filters(self):
        res = self.client.get(
            MOVIE_LIST_URL, {
                "actors": f"{self.actor1.id}",
                "genres": f"{self.genre1.id}",
                "title": self.movie1.title
            }
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        movies = (Movie.objects.filter(title=self.movie1.title)
                  .filter(actors__id=self.actor1.id)
                  .filter(genres__id=self.genre1.id))
        serializer1 = MovieListSerializer(self.movie1)
        serializer2 = MovieListSerializer(self.movie2)
        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

    def test_create_movie(self):
        payloads = {
            "title": "test",
            "description": "test",
            "actors": f"{self.actor1.id}",
            "genres": f"{self.genre1.id}",
            "duration": 90
        }
        res = self.client.post(MOVIE_LIST_URL, payloads)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_detail_movie(self):
        res = self.client.get(detail_url(self.movie1.id))
        serializer1 = MovieDetailSerializer(self.movie1)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer1.data)


class AdminMovieListAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user_admin = get_user_model().objects.create_user(
            email="adminemail@test.com",
            password="adminPass",
            is_staff=True
        )
        self.client.force_authenticate(self.user_admin)
        self.actor1 = sample_actor()
        self.genre1 = sample_genre(name="test")
        self.actor2 = sample_actor()
        self.genre2 = sample_genre(name="test2")

    def test_create_movies(self):
        payloads = {
            "title": "test",
            "description": "test",
            "actors": f"{self.actor1.id}",
            "genres": f"{self.genre1.id}",
            "duration": 90
        }
        res = self.client.post(MOVIE_LIST_URL, payloads)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie1 = Movie.objects.get(id=res.data["id"])
        serializer1 = MovieSerializer(movie1)
        self.assertEqual(res.data, serializer1.data)

    def test_update_movies(self):
        payloads = {
            "title": "new test",
            "description": "new test",
            "actors": f"{self.actor2.id}",
            "genres": f"{self.genre2.id}",
            "duration": 105
        }
        movie1 = sample_movie()
        res = self.client.put(detail_url(movie1.id), data=payloads)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        res = self.client.patch(detail_url(movie1.id),data={"title": "new test"})
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_movie(self):
        movie = sample_movie()
        res = self.client.delete(detail_url(movie.id))
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
