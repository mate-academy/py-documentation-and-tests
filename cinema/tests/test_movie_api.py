import tempfile
import os

from PIL import Image
from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from cinema.models import Movie, Genre, Actor
from cinema.serializers import (
    MovieListSerializer,
    MovieDetailSerializer,
    MovieImageSerializer,
    MovieSerializer,
)
from cinema.views import MovieViewSet

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


class MovieViewSetPermissionTestCase(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@user.com", password="13flrmkgse"
        )
        self.super_user = get_user_model().objects.create_superuser(
            email="test@super_user.com", password="13flrmkgse"
        )

    def test_unauthenticated_user_get_request(self):
        result = self.client.get(reverse("cinema:movie-list"))
        self.assertEqual(result.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_user_get_request(self):
        self.client.force_authenticate(self.user)
        result = self.client.get(reverse("cinema:movie-list"))
        self.assertEqual(result.status_code, status.HTTP_200_OK)

    def test_authenticated_user_post_request_forbidden(self):
        self.client.force_authenticate(self.user)
        result = self.client.post(reverse("cinema:movie-list"))
        self.assertEqual(result.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_superuser_post_request_allowed(self):
        self.client.force_authenticate(self.super_user)
        path = reverse("cinema:movie-list")
        data = {
            "title": "Sample movie",
            "description": "Sample description",
            "duration": 90,
            "genres": [sample_genre().id],
            "actors": [sample_actor().id],
        }
        result = self.client.post(path=path, data=data)
        self.assertEqual(result.status_code, status.HTTP_201_CREATED)


class MovieViewSetGetQuerySetTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@user.com", password="13flrmkgse"
        )
        self.client.force_authenticate(self.user)

        self.top_gun = sample_movie(title="Top Gun")
        self.snatch = sample_movie(title="Snatch")

        self.action = sample_genre(name="Action")
        self.comedy = sample_genre(name="Comedy")

        self.tom_cruise = sample_actor(first_name="Tom", last_name="Cruise")
        self.brad_pitt = sample_actor(first_name="Brad", last_name="Pitt")

        self.top_gun.genres.add(self.action)
        self.top_gun.actors.add(self.tom_cruise)

        self.snatch.genres.add(self.comedy)
        self.snatch.actors.add(self.brad_pitt)

    def test_get_queryset_title_filter(self):
        url = reverse("cinema:movie-list")
        query_params = {"title": "Top Gun"}
        response = self.client.get(url, query_params)
        serializer_top_gun = MovieListSerializer(self.top_gun)
        serializer_all_movie = MovieListSerializer(
            Movie.objects.all(), many=True
        )

        self.assertIn(serializer_top_gun.data, response.data)
        self.assertNotEqual(serializer_all_movie.data, serializer_top_gun)

    def test_get_queryset_actors_filter(self):
        url = reverse("cinema:movie-list")
        response_all_actors = self.client.get(url, {"actors": "1,2"})
        response_one_actor = self.client.get(url, {"actors": "2"})
        serializer_snatch = MovieListSerializer(self.snatch)
        serializer_all_movie = MovieListSerializer(
            Movie.objects.all(), many=True
        )

        self.assertEqual(serializer_all_movie.data, response_all_actors.data)
        self.assertIn(serializer_snatch.data, response_one_actor.data)
        self.assertNotEqual(serializer_snatch.data, serializer_all_movie.data)

    def test_movie_detail(self):
        response = self.client.get(detail_url(self.top_gun.id))
        serializer = MovieDetailSerializer(self.top_gun)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(serializer.data, response.data)


class MovieViewSetGetSerializerTestCase(TestCase):
    def setUp(self):
        self.client = APIClient
        self.movies_url = reverse("cinema:movie-list")

    def test_get_serializer_list_action(self):
        view = MovieViewSet()
        view.action = "list"
        serializer_class = view.get_serializer_class()
        self.assertEqual(serializer_class, MovieListSerializer)

    def test_get_serializer_retrieve_action(self):
        view = MovieViewSet()
        view.action = "retrieve"
        serializer_class = view.get_serializer_class()
        self.assertEqual(serializer_class, MovieDetailSerializer)

    def test_get_serializer_upload_image_action(self):
        view = MovieViewSet()
        view.action = "upload_image"
        serializer_class = view.get_serializer_class()
        self.assertEqual(serializer_class, MovieImageSerializer)

    def test_get_serializer_default_action(self):
        view = MovieViewSet()
        view.action = "create"
        serializer_class = view.get_serializer_class()
        self.assertEqual(serializer_class, MovieSerializer)
