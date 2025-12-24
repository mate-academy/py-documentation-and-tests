import shutil
import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
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
TEMP_MEDIA_ROOT = tempfile.mkdtemp()


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


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
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

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

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


class MovieAPIViewTests(TestCase):

    def setUp(self):
        self.user_admin = get_user_model().objects.create_superuser(
            "user@test.com", "testpassword"
        )
        self.genre = sample_genre()
        self.actor = sample_actor()
        self.client = APIClient()
        self.client.force_authenticate(self.user_admin)
        self.movie = sample_movie()

    def test_movie_list_action(self):
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_movie_retrieve_action(self):
        movie = Movie.objects.get(pk=self.movie.id)
        serializer = MovieDetailSerializer(movie)
        res = self.client.get(
            reverse("cinema:movie-detail", kwargs={"pk": self.movie.id})
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_movie_view_authorized_only(self):
        self.client.logout()
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        res = self.client.post(
            MOVIE_URL, {"title": "Title", "description": "Description"}
        )
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        res = self.client.delete(
            reverse("cinema:movie-detail", kwargs={"pk": self.movie.id})
        )
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        res = self.client.put(
            reverse("cinema:movie-detail", kwargs={"pk": self.movie.id}),
            {"title": "Title", "description": "Description", "duration": 90},
        )
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        res = self.client.patch(
            reverse("cinema:movie-detail", kwargs={"pk": self.movie.id}),
            {"title": "Title"},
        )
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_movie_default_user_read_only(self):
        self.user_admin.is_staff = False
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        res = self.client.get(
            reverse("cinema:movie-detail", kwargs={"pk": self.movie.id})
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        res = self.client.post(
            MOVIE_URL,
            {"title": "Title", "description": "Description", "duration": 90},
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        res = self.client.put(
            reverse("cinema:movie-detail", kwargs={"pk": self.movie.id}),
            {"title": "Title", "description": "Description", "duration": 90},
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        res = self.client.patch(
            reverse("cinema:movie-detail", kwargs={"pk": self.movie.id}),
            {"title": "Title"},
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        res = self.client.delete(
            reverse("cinema:movie-detail", kwargs={"pk": self.movie.id})
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_movie_delete_forbidden_for_all(self):
        url = reverse("cinema:movie-detail", kwargs={"pk": self.movie.id})
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertTrue(Movie.objects.filter(pk=self.movie.id).exists())

    def test_movie_update_forbidden_for_all(self):
        url = reverse("cinema:movie-detail", kwargs={"pk": self.movie.id})
        res = self.client.put(url, {"title": "New Title"})
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual("Sample movie", self.movie.title)

    def test_movie_create_allowed_for_admin_only(self):
        self.user_admin.is_staff = False
        res = self.client.post(
            MOVIE_URL,
            {
                "title": "New Title",
                "description": "Description",
                "duration": 100,
                "genres": [1],
                "actors": [1],
            },
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        self.user_admin.is_staff = True
        res = self.client.post(
            MOVIE_URL,
            {
                "title": "New Title",
                "description": "Description",
                "duration": 100,
                "genres": [1],
                "actors": [1],
            },
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_movie_search_by_title(self):
        searched_movie = Movie.objects.create(
            title="22346",
            description="3344677 Description",
            duration=100,
        )
        not_searched_movie = Movie.objects.create(
            title="87875",
            description="dadbasdzxc",
            duration=100,
        )
        res = self.client.get(
            MOVIE_URL, query_params={"title": searched_movie.title}
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertContains(res, searched_movie.description)
        self.assertNotContains(res, not_searched_movie.description)

    def test_movie_search_by_actors(self):
        searched_movie = Movie.objects.create(
            title="22346",
            description="3344677 Description",
            duration=100,
        )
        not_searched_movie = Movie.objects.create(
            title="87875",
            description="dadbasdzxc",
            duration=100,
        )
        searched_movie.actors.add(self.actor)
        res = self.client.get(
            MOVIE_URL, query_params={"actors": self.actor.id}
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertContains(res, searched_movie.description)
        self.assertNotContains(res, not_searched_movie.description)

    def test_movie_search_by_genres(self):
        searched_movie = Movie.objects.create(
            title="22346",
            description="3344677 Description",
            duration=100,
        )
        not_searched_movie = Movie.objects.create(
            title="87875",
            description="dadbasdzxc",
            duration=100,
        )
        searched_movie.genres.add(self.genre)
        res = self.client.get(
            MOVIE_URL, query_params={"genres": self.genre.id}
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertContains(res, searched_movie.description)
        self.assertNotContains(res, not_searched_movie.description)
