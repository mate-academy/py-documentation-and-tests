import tempfile
import os
from datetime import datetime

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor
from cinema.serializers import (
    MovieListSerializer,
    MovieSessionListSerializer,
    GenreSerializer,
    ActorSerializer,
    MovieDetailSerializer,
    MovieSerializer,
    MovieSessionSerializer
)

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
        name="Blue",
        rows=20,
        seats_in_row=20
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


class UnAuthenticatedMovieTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_get_genres_unauthorized(self):
        url = reverse("cinema:genre-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(
            response.data["detail"],
            "Authentication credentials were not provided."
        )

    def test_get_actors_unauthorized(self):
        url = reverse("cinema:actor-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(
            response.data["detail"],
            "Authentication credentials were not provided."
        )

    def test_get_movies_unauthorized(self):
        url = MOVIE_URL
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(
            response.data["detail"],
            "Authentication credentials were not provided."
        )

    def test_get_movie_session_unauthorized(self):
        url = MOVIE_SESSION_URL
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(
            response.data["detail"],
            "Authentication credentials were not provided."
        )


class AuthenticatedMovieTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user@myproject.com", password="password"
        )
        self.client.force_authenticate(user=self.user)
        self.genre = sample_genre()
        self.actor = sample_actor()
        self.movie = sample_movie()
        self.show_time = datetime.now()
        self.movie_session = sample_movie_session(
            movie=self.movie,
            show_time=self.show_time
        )

    def test_get_genres_authorized(self):
        url = reverse("cinema:genre-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_actors_authorized(self):
        url = reverse("cinema:actor-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_movies_authorized(self):
        url = MOVIE_URL
        response = self.client.get(url)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_get_movie_detail_authorized(self):
        url = reverse("cinema:movie-detail", kwargs={"pk": self.movie.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_movie_session_authorized(self):
        url = MOVIE_SESSION_URL
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_movie_session_detail_authorized(self):
        url = reverse(
            "cinema:moviesession-detail",
            kwargs={"pk": self.movie_session.id},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_filter_movie_by_title(self):
        url = MOVIE_URL
        response = self.client.get(url, {"title": self.movie.title})

        serializer = MovieListSerializer(self.movie)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertIn(serializer.data, response.data)

    def test_filter_movie_by_genre(self):
        self.movie.genres.add(self.genre)
        url = MOVIE_URL
        response = self.client.get(url, {"genres": self.genre.id})

        serializer = MovieListSerializer(self.movie)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertIn(serializer.data, response.data)

    def test_filter_movie_by_actors(self):
        self.movie.actors.add(self.actor)
        url = MOVIE_URL
        response = self.client.get(url, {"actors": self.actor.id})

        serializer = MovieListSerializer(self.movie)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertIn(serializer.data, response.data)

    def test_filter_movie_session_by_date(self):
        url = MOVIE_SESSION_URL
        date = self.show_time.strftime("%Y-%m-%d")
        response = self.client.get(url, data={"date": date})

        movie_sessions = MovieSession.objects.filter(show_time__date=date)
        serializer = MovieSessionListSerializer(movie_sessions, many=True)

        for session in response.data:
            session.pop("tickets_available", None)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data, serializer.data)

    def test_filter_movie_session_by_movie(self):
        url = MOVIE_SESSION_URL
        response = self.client.get(url, data={"movie": self.movie.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        movie_sessions = MovieSession.objects.filter(movie=self.movie)
        serializer = MovieSessionListSerializer(movie_sessions, many=True)

        for session in response.data:
            session.pop("tickets_available", None)
        for session in serializer.data:
            session.pop("tickets_available", None)

        self.assertEqual(response.data, serializer.data)


class AdminMovieTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            email="admin@myproject.com", password="password"
        )
        self.client.force_authenticate(user=self.user)
        self.genre = sample_genre()
        self.actor = sample_actor()
        self.movie = sample_movie()
        self.show_time = datetime.now()
        self.movie_session = sample_movie_session(
            movie=self.movie, show_time=self.show_time
        )

    def test_add_genre(self):
        url = reverse("cinema:genre-list")
        data = {"name": "Test Genre"}
        response = self.client.post(url, data)

        serializer = GenreSerializer(Genre.objects.all().last())

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data, serializer.data)

    def test_add_actor(self):
        url = reverse("cinema:actor-list")
        data = {"first_name": "Test", "last_name": "Actor"}
        response = self.client.post(url, data)

        serializer = ActorSerializer(Actor.objects.all().last())

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data, serializer.data)

    def test_create_movie(self):
        url = MOVIE_URL

        data = {
            "title": "Test Movie",
            "description": "Test Description",
            "duration": 120,
            "genres": [self.genre.id],
            "actors": [self.actor.id],
        }
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        movie = Movie.objects.get(id=response.data["id"])

        response_serializer = MovieSerializer(movie)

        self.assertEqual(response.data["title"],
                         response_serializer.data["title"])
        self.assertEqual(response.data["description"],
                         response_serializer.data["description"])
        self.assertEqual(response.data["duration"],
                         response_serializer.data["duration"])
        self.assertEqual(response.data["genres"],
                         [genre.id for genre in movie.genres.all()])
        self.assertEqual(response.data["actors"],
                         [actor.id for actor in movie.actors.all()])

        detail_serializer = MovieDetailSerializer(movie)
        detail_data = detail_serializer.data

        self.assertEqual(response.data["title"], detail_data["title"])
        self.assertEqual(response.data["description"],
                         detail_data["description"])
        self.assertEqual(response.data["duration"], detail_data["duration"])
        self.assertEqual([genre["id"] for genre in detail_data["genres"]],
                         response.data["genres"])
        self.assertEqual([actor["id"] for actor in detail_data["actors"]],
                         response.data["actors"])

    def test_add_movie_session(self):
        url = MOVIE_SESSION_URL
        show_time = datetime.now().isoformat()

        data = {
            "movie": self.movie.id,
            "cinema_hall": 1,
            "show_time": show_time,
        }
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        movie_session = MovieSession.objects.last()
        serializer = MovieSessionSerializer(movie_session)

        self.assertEqual(response.data["movie"], serializer.data["movie"])
        self.assertEqual(response.data["cinema_hall"],
                         serializer.data["cinema_hall"])

        self.assertEqual(
            response.data["show_time"][:19],
            serializer.data["show_time"][:19]
        )
