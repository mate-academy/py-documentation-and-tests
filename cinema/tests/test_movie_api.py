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
        response = self.client.get(MOVIE_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "user@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)
        self.movie_with_genres_and_actors = sample_movie()
        self.movie_without_genres_and_actors_1 = sample_movie(title="Some movie")
        self.movie_without_genres_and_actors_2 = sample_movie(title="Some other movie")
        self.genre = sample_genre()
        self.actor = sample_actor()

        self.movie_with_genres_and_actors.genres.add(self.genre)
        self.movie_with_genres_and_actors.actors.add(self.actor)

    def test_movies_list(self):
        response = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_filter_movies_by_title(self):
        response_with_exist = self.client.get(MOVIE_URL + "?title=some")
        movies_with_exist = Movie.objects.filter(title__icontains="some")
        serializer_with_exist = MovieListSerializer(movies_with_exist, many=True)

        response_without_exist = self.client.get(MOVIE_URL + "?title=non-exist")
        movies_without_exist = Movie.objects.filter(title__icontains="non-exist")
        serializer_without_exist = MovieListSerializer(movies_without_exist, many=True)

        self.assertEqual(response_with_exist.data, serializer_with_exist.data)
        self.assertEqual(response_without_exist.data, serializer_without_exist.data)

    def test_filter_movies_by_genres(self):
        response = self.client.get(MOVIE_URL, {"genres": self.genre.id})

        serializer_with_genres = MovieListSerializer(self.movie_with_genres_and_actors)
        serializer_without_genres = MovieListSerializer(self.movie_without_genres_and_actors_1)

        self.assertIn(serializer_with_genres.data, response.data)
        self.assertNotIn(serializer_without_genres.data, response.data)

    def test_filter_movies_by_actors(self):
        response = self.client.get(MOVIE_URL, {"actors": self.actor.id})

        serializer_with_actors = MovieListSerializer(self.movie_with_genres_and_actors)
        serializer_without_actors = MovieListSerializer(self.movie_without_genres_and_actors_1)

        self.assertIn(serializer_with_actors.data, response.data)
        self.assertNotIn(serializer_without_actors.data, response.data)

    def test_movie_retrieve(self):
        url = detail_url(self.movie_with_genres_and_actors.id)
        response = self.client.get(url)
        serializer = MovieDetailSerializer(self.movie_with_genres_and_actors)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Movie Title",
            "description": "Movie Description",
            "duration": 100,
        }
        response = self.client.post(MOVIE_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser("admin@myproject.com", "password",)
        self.client.force_authenticate(self.user)

        self.movie = sample_movie()
        self.genre_1 = sample_genre()
        self.genre_2 = sample_genre(name="Action")
        self.actor = sample_actor()

    def test_create_movie(self):
        payload = {
            "title": "Movie Title",
            "description": "Movie Description",
            "duration": 100,
            "genres": [self.genre_1.id, self.genre_2.id],
            "actors": self.actor.id
        }
        response = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=response.data["id"])
        genres = movie.genres.all()
        actors = movie.actors.all()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        for key in ("title", "description", "duration"):
            self.assertEqual(payload[key], getattr(movie, key))

        self.assertEqual(list(genres), [self.genre_1, self.genre_2])
        self.assertEqual(list(actors), [self.actor])

    def test_delete_movie_not_allowed(self):
        url = detail_url(self.movie.id)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
