import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from rest_framework.test import APIClient, APITestCase
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


class MovieViewSetTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "user@myproject.com", "password"
        )
        self.admin = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(user=self.user)

        self.genre_scifi = sample_genre(name="science-fiction")
        self.genre_drama = sample_genre(name="drama")
        self.actor_a = sample_actor(first_name="test", last_name="abc")
        self.actor_b = sample_actor(first_name="test", last_name="yxz")

        self.movie_a = sample_movie(title="A", duration=140)
        self.movie_a.genres.add(self.genre_scifi)
        self.movie_a.actors.add(self.actor_a)

        self.movie_b = sample_movie(title="B", duration=80)
        self.movie_b.genres.add(self.genre_drama)
        self.movie_b.actors.add(self.actor_b)

        self.movie_session = sample_movie_session(movie=self.movie_a)

        self.list_url = MOVIE_URL
        self.detail_url_a = reverse("cinema:movie-detail", args=[self.movie_a.id])
        self.detail_url_b = reverse("cinema:movie-detail", args=[self.movie_b.id])

    def test_retrieve_movies_list_success(self):
        res = self.client.get(self.list_url)
        items = Movie.objects.all()
        serializer = MovieListSerializer(items, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(serializer.data, res.data)
        self.assertEqual(len(res.data), 2)

    def test_retrieve_movie_detail_success(self):
        res = self.client.get(self.detail_url_a)
        item = Movie.objects.get(pk=self.movie_a.id)
        serializer = MovieDetailSerializer(item)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(serializer.data, res.data)

    def test_filter_movies_by_title(self):
        url = self.list_url + f"?title={self.movie_a.title}"
        res = self.client.get(url)
        expected = Movie.objects.filter(title=self.movie_a.title)
        serializer = MovieListSerializer(expected, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(serializer.data, res.data)
        self.assertEqual(len(res.data), 1)

    def test_filter_movies_by_genres(self):
        url = self.list_url + f"?genres={self.genre_scifi.id}"
        res = self.client.get(url)
        expected = Movie.objects.filter(genres__id=self.genre_scifi.id)
        serializer = MovieListSerializer(expected, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(serializer.data, res.data)
        self.assertEqual(len(res.data), 1)

    def test_filter_movies_by_actors(self):
        url = self.list_url + f"?actors={self.actor_a.id}"
        res = self.client.get(url)
        expected = Movie.objects.filter(actors__id=self.actor_a.id)
        serializer = MovieListSerializer(expected, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(serializer.data, res.data)
        self.assertEqual(len(res.data), 1)

    def test_create_movie_as_admin_success(self):
        self.client.force_authenticate(user=self.admin)

        payload = {
            "title": "C",
            "duration": 90,
            "description": "abc",
            "genres": [self.genre_scifi.id],
            "actors": [self.actor_a.id]
        }

        res = self.client.post(self.list_url, data=payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        new_movie = Movie.objects.get(title="C")
        expected = MovieListSerializer(new_movie).data
        self.assertEqual(expected["title"], res.data["title"])
        self.assertEqual(expected["duration"], res.data["duration"])
        self.assertEqual(expected["description"], res.data["description"])

    def test_create_movie_forbidden_for_user(self):
        self.client.force_authenticate(user=self.user)

        payload = {
            "title": "C",
            "duration": 90,
            "description": "abc",
        }

        res = self.client.post(self.list_url, data=payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Movie.objects.filter(title="C").exists())

    def test_create_movie_invalid_data(self):
        self.client.force_authenticate(user=self.admin)

        payload = {
            "duration": 90,
            "description": "abc",
        }
        res = self.client.post(self.list_url, data=payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("title", res.data)
