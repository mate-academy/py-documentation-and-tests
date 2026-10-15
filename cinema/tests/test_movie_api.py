import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor
from cinema.serializers import MovieDetailSerializer, MovieListSerializer

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
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com",
            password="1111",
        )
        self.client.force_authenticate(self.user)

    def test_movie_list(self):
        first_test_movie = sample_movie(title="Test1")
        second_test_movie = sample_movie(title="Test2")
        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_movie_detail(self):
        movie = sample_movie()
        serializer = MovieDetailSerializer(movie)
        res = self.client.get(detail_url(movie.id))

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_genres(self):
        first_test_movie = sample_movie()
        second_test_movie = sample_movie()
        third_test_movie = sample_movie()

        first_test_genre = sample_genre(name="horror")
        second_test_genre = sample_genre(name="comedy")
        third_test_genre = sample_genre(name="drama")

        first_test_movie.genres.add(first_test_genre)
        second_test_movie.genres.add(second_test_genre)
        third_test_movie.genres.add(third_test_genre)

        res = self.client.get(
            MOVIE_URL,
            {"genres": f"{first_test_genre.id},{second_test_genre.id}"}
        )

        serializer_horror_movie = MovieListSerializer(first_test_movie)
        serializer_comedy_movie = MovieListSerializer(second_test_movie)
        serializer_drama_movie = MovieListSerializer(third_test_movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer_horror_movie.data, res.data)
        self.assertIn(serializer_comedy_movie.data, res.data)
        self.assertNotIn(serializer_drama_movie.data, res.data)

    def test_filter_movies_by_actors(self):
        first_test_movie = sample_movie()
        second_test_movie = sample_movie()
        third_test_movie = sample_movie()

        first_test_actor = sample_actor(first_name="Ryan", last_name="Gosling")
        second_test_actor = sample_actor(first_name="Arnold", last_name="Swarzenegger")
        third_test_actor = sample_actor(first_name="Bruce", last_name="Li")

        first_test_movie.actors.add(first_test_actor)
        second_test_movie.actors.add(second_test_actor)
        third_test_movie.actors.add(third_test_actor)

        res = self.client.get(
            MOVIE_URL,
            {"actors": f"{first_test_actor.id},{second_test_actor.id}"}
        )

        serializer_first_test_movie = MovieListSerializer(first_test_movie)
        serializer_second_test_movie = MovieListSerializer(second_test_movie)
        serializer_third_test_movie = MovieListSerializer(third_test_movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer_first_test_movie.data, res.data)
        self.assertIn(serializer_second_test_movie.data, res.data)
        self.assertNotIn(serializer_third_test_movie.data, res.data)

    def test_filter_movies_by_title(self):
        first_test_movie = sample_movie(title="Alien")
        second_test_movie = sample_movie(title="Spider-Man")

        res = self.client.get(
            MOVIE_URL,
            {"title": "ALI"}
        )

        serializer_first_test_movie = MovieListSerializer(first_test_movie)
        serializer_second_test_movie = MovieListSerializer(second_test_movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer_first_test_movie.data, res.data)
        self.assertNotIn(serializer_second_test_movie.data, res.data)

    def test_create_movie_forbidden_for_regular_user(self):
        test_genre = sample_genre(name="drama")
        test_actor = sample_actor(first_name="Leo", last_name="DiCaprio")
        payload = {
            "title": "Titanic",
            "description": "Test movie",
            "duration": 90,
            "actors": [test_actor.id],
            "genres": [test_genre.id]
        }
        all_movies_before = Movie.objects.count()
        res = self.client.post(MOVIE_URL, payload, format="json")
        all_movies_after = Movie.objects.count()

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(all_movies_before, all_movies_after)

    def test_upload_image_forbidden_for_regular_user(self):
        movie = sample_movie()
        url = image_upload_url(movie.id)

        with tempfile.NamedTemporaryFile(suffix=".jpg") as image_file:
            image = Image.new("RGB", (10, 10))
            image.save(image_file, format="JPEG")
            image_file.seek(0)
            res = self.client.post(
                url,
                {"image": image_file},
                format="multipart",
            )

        movie.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(movie.image)


class AdminMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user_admin = get_user_model().objects.create_user(
            email="test@test.com",
            password="1111",
            is_staff=True
        )
        self.client.force_authenticate(self.user_admin)

    def test_create_movie_available_for_admin_user(self):
        test_genre = sample_genre(name="drama")
        test_actor = sample_actor(first_name="Leo", last_name="DiCaprio")
        payload = {
            "title": "Titanic",
            "description": "Test movie",
            "duration": 90,
            "actors": [test_actor.id],
            "genres": [test_genre.id]
        }
        all_movies_before = Movie.objects.count()
        res = self.client.post(MOVIE_URL, payload, format="json")
        all_movies_after = Movie.objects.count()
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(all_movies_after, all_movies_before + 1)

        test_movie = Movie.objects.get(id=res.data["id"])

        self.assertEqual(test_movie.title, "Titanic")
        self.assertEqual(test_movie.description, "Test movie")
        self.assertEqual(test_movie.duration, 90)
        self.assertIn(test_actor, test_movie.actors.all())
        self.assertEqual(test_movie.actors.count(), 1)
        self.assertIn(test_genre, test_movie.genres.all())
        self.assertEqual(test_movie.genres.count(), 1)
