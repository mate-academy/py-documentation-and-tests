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


def movie_detail_url(movie_id: int):
    return reverse("cinema:movie-detail", args=[movie_id])


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
        self.user = get_user_model().objects.create_user(
            email="user@create.com", password="adsljfsdfl;"
        )
        self.client.force_authenticate(self.user)

    def test_auth_required(self):
        response = self.client.get(MOVIE_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_movie(self):
        sample_movie()

        movie_with_genre = sample_movie()
        drama_genre = sample_genre()
        movie_with_genre.genres.add(drama_genre)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        response = self.client.get(MOVIE_URL)

        self.assertEqual(response.data, serializer.data)

    def test_filter_movie_by_title(self):
        movie_1 = sample_movie(title="Potter")
        movie_2 = sample_movie(title="Potter 2")
        movie_3 = sample_movie()

        serializer_1 = MovieListSerializer(movie_1)
        serializer_2 = MovieListSerializer(movie_2)
        serializer_3 = MovieListSerializer(movie_3)

        response = self.client.get(MOVIE_URL, {"title": "potter"})

        self.assertIn(serializer_1.data, response.data)
        self.assertIn(serializer_2.data, response.data)
        self.assertNotIn(serializer_3.data, response.data)

    def test_filter_movie_by_genres(self):
        movie_1 = sample_movie()
        movie_2 = sample_movie()
        movie_3 = sample_movie()

        action = sample_genre(name="action")
        dramma = sample_genre(name="dramma")

        movie_1.genres.add(action)
        movie_2.genres.add(dramma)

        serializer_1 = MovieListSerializer(movie_1)
        serializer_2 = MovieListSerializer(movie_2)
        serializer_3 = MovieListSerializer(movie_3)

        response = self.client.get(
            MOVIE_URL, {"genres": f"{action.id}, {dramma.id}"}
        )

        self.assertIn(serializer_1.data, response.data)
        self.assertIn(serializer_2.data, response.data)
        self.assertNotIn(serializer_3.data, response.data)

    def test_filter_movie_by_actors(self):
        movie_1 = sample_movie()
        movie_2 = sample_movie()
        movie_3 = sample_movie()

        dobby = sample_actor(first_name="Dobby", last_name="Dobich")
        rick = sample_actor(first_name="Rick", last_name="Sholz")

        movie_1.actors.add(dobby)
        movie_2.actors.add(rick)

        serializer_1 = MovieListSerializer(movie_1)
        serializer_2 = MovieListSerializer(movie_2)
        serializer_3 = MovieListSerializer(movie_3)

        response = self.client.get(
            MOVIE_URL, {"actors": f"{dobby.id}, {rick.id}"}
        )

        self.assertIn(serializer_1.data, response.data)
        self.assertIn(serializer_2.data, response.data)
        self.assertNotIn(serializer_3.data, response.data)

    def test_retrive_movie_detail(self):
        movie = sample_movie()
        url = detail_url(movie.id)

        response = self.client.get(url)
        serializer = MovieDetailSerializer(movie)

        self.assertEqual(response.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Gamer",
            "description": "Movie about best cyber",
            "duration": 113,
        }
        response = self.client.post(MOVIE_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "test@testik.com", "fasdffewxv", is_staff=True,
        )
        self.client.force_authenticate(self.user)

    def test_create_movie_without_relations(self):
        sample_actor()
        sample_genre()

        payload = {
            "title": "Test movie",
            "description": "Test desc",
            "duration": 113,
        }

        res = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_create_movie_with_relations(self):
        sample_actor()
        sample_genre()

        payload = {
            "title": "Test movie",
            "description": "Test desc",
            "duration": 113,
            "actors": 1,
            "genres": 1,
        }

        res = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=res.data["id"])
        movie_genres = movie.genres.all()
        movie_actors = movie.actors.all()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(movie_genres.count(), 1)
        self.assertEqual(movie_actors.count(), 1)

    def test_delete_movie_not_allowed(self):
        movie = sample_movie()
        url = movie_detail_url(movie.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
