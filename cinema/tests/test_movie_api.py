import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor
from cinema.serializers import (
    MovieListSerializer,
    MovieDetailSerializer,
)

MOVIE_URL = reverse("cinema:movie-list")
MOVIE_SESSION_URL = reverse("cinema:moviesession-list")


def _params_to_ints(qs):
    return [int(str_id) for str_id in qs.split(",")]


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


class UnauthorizedUserMovieTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_access_denied(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthorizedUserMovieTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin.user@test.com", "asdfg6777890"
        )
        self.client.force_authenticate(self.user)

        actor1 = sample_actor(
            first_name="first actor first name",
            last_name="first actor last name",
        )
        actor2 = sample_actor(
            first_name="second actor first name",
            last_name="second actor last name",
        )
        genre1 = sample_genre(name="movie genre")
        genre2 = sample_genre(name="new genre")

        movie1 = sample_movie(title="movie first title")
        movie1.actors.set([actor1, actor2])
        movie1.genres.set([genre1, genre2])

        movie2 = sample_movie(title="another movie nane")
        movie2.actors.set([actor1])
        movie2.genres.set([genre2])

    def test_movie_list_action(self):
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_movie_list_action_with_filter_by_title(self):
        filter_str = "another MOVIE"
        movies = Movie.objects.filter(title__icontains=filter_str)
        serializer = MovieListSerializer(movies, many=True)

        res = self.client.get(MOVIE_URL + f"?title={filter_str}")
        self.assertEqual(res.data, serializer.data)
        self.assertEqual(len(res.data), 1)

        filter_str = "no-match"
        movies = Movie.objects.filter(title__icontains=filter_str)
        serializer = MovieListSerializer(movies, many=True)

        res = self.client.get(MOVIE_URL + f"?title={filter_str}")
        self.assertEqual(res.data, serializer.data)
        self.assertEqual(len(res.data), 0)

    def test_movie_list_action_with_filter_by_genres(self):
        genre = Genre.objects.get(pk=1)

        filter_str = f"{genre.id},12345"
        filter_list = _params_to_ints(filter_str)
        movies = Movie.objects.filter(genres__in=filter_list)
        serializer = MovieListSerializer(movies, many=True)

        res = self.client.get(MOVIE_URL + f"?genres={filter_str}")
        self.assertEqual(res.data, serializer.data)
        self.assertEqual(len(res.data), 1)

        filter_str = "0"
        filter_list = _params_to_ints(filter_str)
        movies = Movie.objects.filter(genres__in=filter_list)
        serializer = MovieListSerializer(movies, many=True)

        res = self.client.get(MOVIE_URL + f"?genres={filter_str}")
        self.assertEqual(res.data, serializer.data)
        self.assertEqual(len(res.data), 0)

    def test_movie_list_action_with_filter_by_actors(self):
        actor = Actor.objects.get(pk=1)

        filter_str = f"{actor.id},12345"
        filter_list = _params_to_ints(filter_str)
        movies = Movie.objects.filter(actors__in=filter_list)
        serializer = MovieListSerializer(movies, many=True)

        res = self.client.get(MOVIE_URL + f"?actors={filter_str}")
        self.assertEqual(res.data, serializer.data)
        self.assertEqual(len(res.data), 2)

        filter_str = "0"
        filter_list = _params_to_ints(filter_str)
        movies = Movie.objects.filter(actors__in=filter_list)
        serializer = MovieListSerializer(movies, many=True)

        res = self.client.get(MOVIE_URL + f"?actors={filter_str}")
        self.assertEqual(res.data, serializer.data)
        self.assertEqual(len(res.data), 0)

    def test_movie_retrieve_action(self):
        movie = Movie.objects.get(pk=1)
        serializer = MovieDetailSerializer(movie, many=False)

        url = detail_url(movie.id)
        res = self.client.get(url)
        self.assertTrue(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_movie_create_action(self):
        actors = [row.id for row in Actor.objects.all()]
        genres = [row.id for row in Genre.objects.filter(pk=1)]

        movie = {
            "title": "Sample movie",
            "description": "Sample description",
            "duration": 90,
            "actors": actors,
            "genres": genres,
        }

        res = self.client.post(MOVIE_URL, data=movie)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        for key in movie:
            self.assertEqual(res.data[key], movie[key])

    def test_movie_create_action_without_actors(self):
        genres = list(Genre.objects.filter(pk=1))

        movie = {
            "title": "Sample movie",
            "description": "Sample description",
            "duration": 90,
            "actors": [],
            "genres": genres,
        }

        res = self.client.post(MOVIE_URL, data=movie)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_movie_create_action_without_genres(self):
        actors = list(Actor.objects.all())

        movie = {
            "title": "Sample movie",
            "description": "Sample description",
            "duration": 90,
            "actors": actors,
            "genres": [],
        }

        res = self.client.post(MOVIE_URL, data=movie)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_movie_with_invalid_actions(self):
        movie = Movie.objects.get(pk=1)

        res = self.client.put(MOVIE_URL, data={})
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        res = self.client.delete(MOVIE_URL, data={})
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        url = detail_url(movie.id)

        res = self.client.post(url, data={})
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        res = self.client.put(url, data={})
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        res = self.client.delete(url, data={})
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
