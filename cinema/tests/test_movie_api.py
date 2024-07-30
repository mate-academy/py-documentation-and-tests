import tempfile

import os


from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient


from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor
from cinema.serializers import (
    MovieDetailSerializer,
    MovieListSerializer,
)

MOVIE_URL = reverse("cinema:movie-list")
MOVIE_SESSION_URL = reverse("cinema:moviesession-list")


def sample_movie(**params) -> Movie:
    defaults = {
        "title": "Sample movie",
        "description": "Sample description",
        "duration": 90,
    }
    defaults.update(params)

    return Movie.objects.create(**defaults)


def sample_genre(**params) -> Genre:
    defaults = {
        "name": "Drama",
    }
    defaults.update(params)

    return Genre.objects.create(**defaults)


def sample_actor(**params) -> Actor:
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


class UnauthenticatedCinemaApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedCinemaApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="tesst@test.test",
            password="test",
        )
        self.client.force_authenticate(self.user)

        self.genre1 = sample_genre()
        self.genre2 = sample_genre(name="Action")
        self.genre3 = sample_genre(name="Comedy")

        self.actor1 = sample_actor()
        self.actor2 = sample_actor(first_name="Robin", last_name="Wright")
        self.actor3 = sample_actor(first_name="Charliz", last_name="Theron")

        self.movie1 = sample_movie()
        self.movie2 = sample_movie(
            title="Some film", description="Some description", duration=45
        )
        self.movie3 = sample_movie(
            title="Ice age film", description="A lot of snow", duration=66
        )

        self.movie2.genres.add(self.genre1, self.genre2)
        self.movie3.genres.add(self.genre1, self.genre2, self.genre3)

        self.movie2.actors.add(self.actor1, self.actor2)
        self.movie3.actors.add(self.actor1, self.actor2, self.actor3)

        self.serializer1 = MovieListSerializer(self.movie1)
        self.serializer2 = MovieListSerializer(self.movie2)
        self.serializer3 = MovieListSerializer(self.movie3)

    def asserts_for_test_filter(self, res):
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertNotIn(self.serializer1.data, res.data)
        self.assertIn(self.serializer2.data, res.data)
        self.assertIn(self.serializer3.data, res.data)

    def test_movie_list(self):
        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serialazer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serialazer.data)

    def test_movie_list_filter_genres(self):
        res = self.client.get(
            MOVIE_URL, {"genres": f"{self.genre2.id}, {self.genre3.id}"}
        )
        self.asserts_for_test_filter(res)

    def test_movie_list_filter_actors(self):
        res = self.client.get(
            MOVIE_URL, {"actors": f"{self.actor2.id}, {self.actor3.id}"}
        )
        self.asserts_for_test_filter(res)

    def test_movie_list_filter_actors(self):
        res = self.client.get(MOVIE_URL, {"title": "film"})
        self.asserts_for_test_filter(res)

    def test_retrieve_movie_detail(self):
        url = detail_url(self.movie3.id)
        res = self.client.get(url)
        serialzer = MovieDetailSerializer(self.movie3)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serialzer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Test Movie",
            "description": "Test Movie Description",
            "duration": "55",
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create(
            email="admin@test.com", password="password", is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        payload = {
            "title": "Movie",
            "description": "Description",
            "duration": 90,
        }

        response = self.client.post(MOVIE_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(id=response.data["id"])

        for key, value in payload.items():
            self.assertEqual(value, getattr(movie, key))

    def test_create_movie_with_relations(self):
        genre1 = Genre.objects.create(name="Action")
        genre2 = Genre.objects.create(name="Drama")
        actor1 = Actor.objects.create(first_name="Stana", last_name="Katic")
        actor2 = Actor.objects.create(first_name="Margo", last_name="Robie")

        payload = {
            "title": "Movie 2",
            "description": "Description 2",
            "duration": 50,
            "genres": [genre1.id, genre2.id],
            "actors": [actor1.id, actor2.id],
        }

        response = self.client.post(MOVIE_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        movie = Movie.objects.get(id=response.data["id"])
        actors = movie.actors.all()
        genres = movie.genres.all()

        self.assertIn(actor1, actors)
        self.assertIn(actor2, actors)
        self.assertEqual(actors.count(), 2)
        self.assertIn(genre1, genres)
        self.assertIn(genre2, genres)
        self.assertEqual(genres.count(), 2)

    def test_delete_movie_not_allowed(self):
        movie = sample_movie()
        url = detail_url(movie.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
