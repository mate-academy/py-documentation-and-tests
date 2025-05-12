import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.status import (
    HTTP_401_UNAUTHORIZED,
    HTTP_201_CREATED,
    HTTP_200_OK,
    HTTP_403_FORBIDDEN,
)

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
        url = MOVIE_URL
        res = self.client.get(url)
        self.assertEqual(res.status_code, HTTP_401_UNAUTHORIZED)

        res = self.client.post(url)
        self.assertEqual(res.status_code, HTTP_401_UNAUTHORIZED)

        url = detail_url(1)
        res = self.client.get(url)
        self.assertEqual(res.status_code, HTTP_401_UNAUTHORIZED)

        res = self.client.delete(url)
        self.assertEqual(res.status_code, HTTP_401_UNAUTHORIZED)

        res = self.client.put(url)
        self.assertEqual(res.status_code, HTTP_401_UNAUTHORIZED)

        res = self.client.patch(url)
        self.assertEqual(res.status_code, HTTP_401_UNAUTHORIZED)

        url = reverse("cinema:movie-upload-image", args=[1])
        res = self.client.patch(url)
        self.assertEqual(res.status_code, HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)
        self.movies = [
            sample_movie(title=f"Sample movie{movie_id}")
            for movie_id in range(5)
        ]
        self.genres = [
            sample_genre(name=f"Genre {genre_id}") for genre_id in range(5)
        ]
        self.actors = [
            sample_actor(
                first_name=f"First name {actor_id}",
                last_name=f"Last name {actor_id}",
            )
            for actor_id in range(5)
        ]
        self.movie_sessions = [
            sample_movie_session(movie=self.movies[movie_session_id])
            for movie_session_id in range(5)
        ]

    def test_movies_list(self):
        res = self.client.post(
            MOVIE_URL,
            data={
                "title": "Created movie",
                "description": "Description of created movie",
                "duration": 100,
                "genres": [self.genres[0].id, self.genres[1].id],
                "actors": [self.actors[0].id, self.actors[1].id],
            },
        )

        self.assertEqual(res.status_code, HTTP_201_CREATED)
        movies = Movie.objects.all()

        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, HTTP_200_OK)
        self.assertEqual(res.data, MovieListSerializer(movies, many=True).data)

    def test_no_admin_cannot_create_movie(self):
        self.user.is_staff = False
        self.user.save()

        res = self.client.post(
            MOVIE_URL,
            data={
                "title": "Created movie",
                "description": "Description of created movie",
                "duration": 100,
                "genres": [self.genres[0].id, self.genres[1].id],
                "actors": [self.actors[0].id, self.actors[1].id],
            },
        )

        self.assertEqual(res.status_code, HTTP_403_FORBIDDEN)

    def test_filter_movies_by_title(self):
        title_filter = "E3"
        movies = Movie.objects.filter(title__icontains=title_filter)

        res = self.client.get(MOVIE_URL, {"title": title_filter})

        self.assertEqual(res.status_code, HTTP_200_OK)
        self.assertEqual(res.data, MovieListSerializer(movies, many=True).data)

        title_filter = "No films with title"
        movies = Movie.objects.filter(title__icontains=title_filter)
        res = self.client.get(MOVIE_URL, {"title": title_filter})

        self.assertEqual(res.status_code, HTTP_200_OK)
        self.assertEqual(len(res.data), 0)
        self.assertEqual(res.data, MovieListSerializer(movies, many=True).data)

    def test_filter_movies_by_genres(self):
        genres_ids = [self.genres[0].id, self.genres[1].id]

        self.movies[0].genres.add(self.genres[0])
        self.movies[4].genres.add(self.genres[1])

        movies = Movie.objects.filter(genres__id__in=genres_ids)

        res = self.client.get(
            MOVIE_URL, {"genres": f"{genres_ids[0]},{genres_ids[1]}"}
        )

        self.assertEqual(res.status_code, HTTP_200_OK)
        self.assertEqual(len(res.data), 2)
        self.assertEqual(res.data, MovieListSerializer(movies, many=True).data)

    def test_filter_movies_by_actors(self):
        actors_ids = [self.actors[0].id, self.actors[1].id]

        self.movies[1].actors.add(self.actors[0])
        self.movies[2].actors.add(self.actors[1])

        movies = Movie.objects.filter(actors__id__in=actors_ids)

        res = self.client.get(
            MOVIE_URL, {"actors": f"{actors_ids[0]},{actors_ids[1]}"}
        )

        self.assertEqual(res.status_code, HTTP_200_OK)
        self.assertEqual(len(res.data), 2)
        self.assertEqual(res.data, MovieListSerializer(movies, many=True).data)

    def test_retrieve_movie_detail(self):
        movie = self.movies[0]
        movie.actors.add(self.actors[0], self.actors[1])
        movie.genres.add(self.genres[0], self.genres[1], self.genres[2])

        res = self.client.get(detail_url(movie.id))

        self.assertEqual(res.status_code, HTTP_200_OK)
        self.assertEqual(res.data, MovieDetailSerializer(movie).data)
