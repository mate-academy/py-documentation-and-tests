import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APITestCase, APIClient
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


class TestUnauthenticatedMovieViewSet(APITestCase):
    def test_auth_required(self):
        response = self.client.get(MOVIE_URL)
        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED
        )


class TestAuthenticatedMovieViewSet(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="user@gmail.com", password="1qazcde3"
        )
        self.client.force_authenticate(self.user)

        self.vikings = sample_movie(title="Vikings")
        self.odyssey = sample_movie(title="Odyssey")
        self.vikings_serializer = MovieListSerializer(self.vikings)
        self.odyssey_serializer = MovieListSerializer(self.odyssey)


    def test_list_movies(self):
        sample_movie()
        sample_movie()

        response = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )
        self.assertEqual(
            response.data,
            serializer.data
        )

    def test_list_movies_filter_by_title(self):
        response = self.client.get(MOVIE_URL, query_params={
            "title": "vik"
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(self.vikings_serializer.data, response.data)
        self.assertNotIn(self.odyssey_serializer.data, response.data)

    def test_list_movies_filter_by_genres(self):
        history = sample_genre(name="History")
        action = sample_genre(name="Action")
        drama = sample_genre()

        self.vikings.genres.set([history, action])
        self.odyssey.genres.set([history, drama])

        response = self.client.get(MOVIE_URL, query_params={
            "genres": f"{history.pk}"
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(self.vikings_serializer.data, response.data)
        self.assertIn(self.odyssey_serializer.data, response.data)

        response = self.client.get(MOVIE_URL, query_params={
            "genres": f"{action.pk}"
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(self.vikings_serializer.data, response.data)
        self.assertNotIn(self.odyssey_serializer.data, response.data)

        response = self.client.get(MOVIE_URL, query_params={
            "genres": f"{drama.pk}"
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn(self.vikings_serializer.data, response.data)
        self.assertIn(self.odyssey_serializer.data, response.data)

    def test_list_movies_filter_by_actors(self):
        ragnar = sample_actor(first_name="Travis", last_name="Fimmel")
        odysseus = sample_actor(first_name="Mett", last_name="Damon")
        test = sample_actor()

        self.vikings.actors.set([ragnar.pk, test.pk])
        self.odyssey.actors.set([odysseus.pk, test.pk])

        response = self.client.get(MOVIE_URL, query_params={
            "actors": f"{test.pk}"
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(self.vikings_serializer.data, response.data)
        self.assertIn(self.odyssey_serializer.data, response.data)

        response = self.client.get(MOVIE_URL, query_params={
            "actors": f"{ragnar.pk}"
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(self.vikings_serializer.data, response.data)
        self.assertNotIn(self.odyssey_serializer.data, response.data)

        response = self.client.get(MOVIE_URL, query_params={
            "actors": f"{odysseus.pk}"
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn(self.vikings_serializer.data, response.data)
        self.assertIn(self.odyssey_serializer.data, response.data)

    def test_movie_detail(self):
        response = self.client.get(detail_url(self.vikings.id))
        serializer = MovieDetailSerializer(self.vikings)
        self.assertEqual(response.data, serializer.data)

    def test_movie_create_forbidden(self):
        data = {
            "title": "Walking Dead",
            "description": "About Walking Dead",
            "duration": 120
        }
        response = self.client.post(MOVIE_URL, data=data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class TestAdminMovieViewSet(APITestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            email="admin@gmail.com", password="1qazcde3"
        )
        self.client.force_authenticate(self.admin)
        self.vikings = sample_movie(title="Vikings")

    def test_movie_create_allow(self):
        actor = sample_actor()
        genre = sample_genre()

        data = {
            "title": "Walking Dead",
            "description": "About Walking Dead",
            "duration": 120,
            "genres": [genre.pk],
            "actors": [actor.pk]
        }
        response = self.client.post(MOVIE_URL, data=data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
