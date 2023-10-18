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


class AnonimMovieApiTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_without_login(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@test.com", "testpass"
        )
        self.client.force_authenticate(self.user)
        self.genre1 = Genre.objects.create(name="test genre")
        self.genre2 = Genre.objects.create(name="another test genre")
        self.actor = Actor.objects.create(
            first_name="Ivan", last_name="Tester"
        )
        self.movie = Movie.objects.create(
            title="Test1",
            description="TEST1",
            duration="110",
        )
        self.second_movie = Movie.objects.create(
            title="Test title2",
            description="TEST description2",
            duration="100",
        )
        self.movie.save()
        self.second_movie.genres.add(self.genre1, self.genre2)
        self.second_movie.actors.add(self.actor)
        self.second_movie.save()

    def test_list_movies(self):
        res = self.client.get(MOVIE_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_by_title(self):
        response = self.client.get(MOVIE_URL, {"title": "Test Movie"})
        movies = Movie.objects.filter(title__icontains="Test Movie")
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_filter_by_genre(self):
        response = self.client.get(MOVIE_URL, {"genres": self.genre1.id})
        movies = Movie.objects.filter(genres=self.genre1)
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_filter_by_actor(self):
        response = self.client.get(MOVIE_URL, {"actors": self.actor.id})
        movies = Movie.objects.filter(actors=self.actor)
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_filter_by_multiple_criteria(self):
        response = self.client.get(
            MOVIE_URL, {"title": "Test Movie", "genres": self.genre1.id}
        )
        movies = Movie.objects.filter(
            title__icontains="Test Movie", genres=self.genre1
        )
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_filter_by_invalid_genre(self):
        response = self.client.get(MOVIE_URL, {"genres": 999})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_filter_by_invalid_actor(self):
        response = self.client.get(MOVIE_URL, {"actors": 999})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_retrieve_movie(self):
        url = detail_url(self.movie.id)
        res = self.client.get(url)

        movie = Movie.objects.get(pk=1)
        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        movie_data = {
            "title": "Test Movie",
            "description": "Test Description",
            "duration": 120,
            "genres": [],
            "actors": [],
        }

        response = self.client.post(MOVIE_URL, movie_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@test.com",
            "testpass",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)
        self.movie = Movie.objects.create(
            title="Test1",
            description="TEST1",
            duration="110",
        )
        self.movie.save()

    def test_create_movie_success(self):
        genre1 = Genre.objects.create(name="Action")
        genre2 = Genre.objects.create(name="Comedy")

        actor1 = Actor.objects.create(first_name="John", last_name="Doe")
        actor2 = Actor.objects.create(first_name="Jane", last_name="Doe")

        movie_data = {
            "title": "Test Movie",
            "description": "Test Description",
            "duration": 120,
            "genres": [genre1.id, genre2.id],
            "actors": [actor1.id, actor2.id],
        }

        response = self.client.post(MOVIE_URL, movie_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_update_movie_forbidden(self):
        movie_id = self.movie.id

        updated_data = {
            "title": "Updated Test Movie",
            "description": "Updated Test Description",
            "duration": 150,
        }
        url = detail_url(movie_id)
        response_update = self.client.put(url, updated_data, format="json")
        self.assertEqual(
            response_update.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )
        response_update = self.client.patch(url, updated_data, format="json")
        self.assertEqual(
            response_update.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def test_delete_movie(self):
        movie_id = self.movie.id

        url = detail_url(movie_id)
        response_delete = self.client.delete(url)
        self.assertEqual(
            response_delete.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )


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
