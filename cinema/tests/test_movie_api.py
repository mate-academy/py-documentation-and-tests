import os
import tempfile

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import Actor, CinemaHall, Genre, Movie, MovieSession

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
    defaults = {"name": "Drama"}
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
        seats_in_row=20,
    )
    defaults = {
        "show_time": "2022-06-02 14:00:00",
        "movie": None,
        "cinema_hall": cinema_hall,
    }
    defaults.update(params)
    return MovieSession.objects.create(**defaults)


def image_upload_url(movie_id):
    return reverse("cinema:movie-upload-image", args=[movie_id])


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


class PublicMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_not_required_for_movie_list(self):
        sample_movie()

        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_auth_not_required_for_movie_detail(self):
        movie = sample_movie()

        res = self.client.get(detail_url(movie.id))

        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_create_movie_forbidden_for_anonymous_user(self):
        genre = sample_genre()
        actor = sample_actor()
        payload = {
            "title": "Test movie",
            "description": "Test description",
            "duration": 120,
            "genres": [genre.id],
            "actors": [actor.id],
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user@test.com",
            password="testpass123",
        )
        self.client.force_authenticate(self.user)

    def test_create_movie_forbidden_for_not_admin_user(self):
        genre = sample_genre()
        actor = sample_actor()
        payload = {
            "title": "Test movie",
            "description": "Test description",
            "duration": 120,
            "genres": [genre.id],
            "actors": [actor.id],
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = get_user_model().objects.create_superuser(
            email="admin@test.com",
            password="testpass123",
        )
        self.client.force_authenticate(self.admin)

    def test_create_movie(self):
        genre = sample_genre()
        actor = sample_actor()
        payload = {
            "title": "Test movie",
            "description": "Test description",
            "duration": 120,
            "genres": [genre.id],
            "actors": [actor.id],
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(id=res.data["id"])
        self.assertEqual(movie.title, payload["title"])
        self.assertIn(genre, movie.genres.all())
        self.assertIn(actor, movie.actors.all())

    def test_retrieve_movie_detail(self):
        genre = sample_genre()
        actor = sample_actor()
        movie = sample_movie()
        movie.genres.add(genre)
        movie.actors.add(actor)

        res = self.client.get(detail_url(movie.id))

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["title"], movie.title)
        self.assertEqual(res.data["genres"][0]["name"], genre.name)
        self.assertEqual(res.data["actors"][0]["full_name"], actor.full_name)

    def test_filter_movies_by_title(self):
        movie_1 = sample_movie(title="Inception")
        movie_2 = sample_movie(title="Titanic")

        res = self.client.get(MOVIE_URL, {"title": "incep"})

        titles = [movie["title"] for movie in res.data]
        self.assertIn(movie_1.title, titles)
        self.assertNotIn(movie_2.title, titles)

    def test_filter_movies_by_genres(self):
        genre_1 = sample_genre(name="Action")
        genre_2 = sample_genre(name="Drama")
        movie_1 = sample_movie(title="Action movie")
        movie_2 = sample_movie(title="Drama movie")
        movie_1.genres.add(genre_1)
        movie_2.genres.add(genre_2)

        res = self.client.get(MOVIE_URL, {"genres": str(genre_1.id)})

        titles = [movie["title"] for movie in res.data]
        self.assertIn(movie_1.title, titles)
        self.assertNotIn(movie_2.title, titles)

    def test_filter_movies_by_actors(self):
        actor_1 = sample_actor(first_name="Leonardo", last_name="DiCaprio")
        actor_2 = sample_actor(first_name="Tom", last_name="Hardy")
        movie_1 = sample_movie(title="Movie with Leonardo")
        movie_2 = sample_movie(title="Movie with Tom")
        movie_1.actors.add(actor_1)
        movie_2.actors.add(actor_2)

        res = self.client.get(MOVIE_URL, {"actors": str(actor_1.id)})

        titles = [movie["title"] for movie in res.data]
        self.assertIn(movie_1.title, titles)
        self.assertNotIn(movie_2.title, titles)


class MovieImageUploadTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            email="admin@myproject.com",
            password="password",
        )
        self.client.force_authenticate(self.user)
        self.movie = sample_movie()
        self.genre = sample_genre()
        self.actor = sample_actor()
        self.movie_session = sample_movie_session(movie=self.movie)

    def tearDown(self):
        if self.movie.image:
            self.movie.image.delete()

    def test_upload_image_to_movie(self):
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
        url = image_upload_url(self.movie.id)

        res = self.client.post(
            url,
            {"image": "not image"},
            format="multipart",
        )

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
                    "genres": [self.genre.id],
                    "actors": [self.actor.id],
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

    def test_image_url_is_shown_on_movie_session_list(self):
        url = image_upload_url(self.movie.id)

        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")

        res = self.client.get(MOVIE_SESSION_URL)

        self.assertIn("movie_image", res.data[0].keys())