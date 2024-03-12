import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

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


class UnauthenticatedMovieTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_authenticate_required(self):
        response = self.client.get(MOVIE_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "user@user.com",
            "qwerty1234",
        )
        self.client.force_authenticate(self.user)

    def test_movies_list(self):
        sample_movie()
        movie_with_genres_and_actors = sample_movie()

        movie_with_genres_and_actors.genres.add(sample_genre())
        movie_with_genres_and_actors.actors.add(sample_actor())

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        response = self.client.get(MOVIE_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_movies_filter_by_actors(self):
        test_test_movie1 = sample_movie()
        test_test_movie2 = sample_movie(title="movie_test_2")

        test_test_actor1 = sample_actor()
        test_test_actor2 = sample_actor(
            first_name="test_first_name", 
            last_name="test_last_name"
        )

        test_test_movie1.actors.add(test_test_actor1)
        test_test_movie2.actors.add(test_test_actor2)

        test_test_movie3 = sample_movie(title="test_movie_3")

        response = self.client.get(
            MOVIE_URL,
            {"actors": f"{test_test_actor1.id},{test_test_actor2.id}"}
        )

        serializer1 = MovieListSerializer(test_test_movie1)
        serializer2 = MovieListSerializer(test_test_movie2)
        serializer3 = MovieListSerializer(test_test_movie3)

        self.assertIn(serializer1.data, response.data)
        self.assertIn(serializer2.data, response.data)
        self.assertNotIn(serializer3.data, response.data)

    def test_movies_filter_by_genres(self):
        test_test_movie1 = sample_movie()
        test_movie2 = sample_movie(title="test_movie_2")

        test_genre1 = sample_genre()
        test_genre2 = sample_genre(name="test_genre")

        test_test_movie1.genres.add(test_genre1)
        test_movie2.genres.add(test_genre2)

        test_movie3 = sample_movie(title="test_movie3")

        response = self.client.get(
            MOVIE_URL,
            {"genres": f"{test_genre1.id},{test_genre2.id}"}
        )

        serializer1 = MovieListSerializer(test_test_movie1)
        serializer2 = MovieListSerializer(test_movie2)
        serializer3 = MovieListSerializer(test_movie3)

        self.assertIn(serializer1.data, response.data)
        self.assertIn(serializer2.data, response.data)
        self.assertNotIn(serializer3.data, response.data)

    def test_movies_filter_by_title(self):
        test_movie1 = sample_movie()
        test_movie2 = sample_movie(title="test_movie2")

        response = self.client.get(
            MOVIE_URL,
            {"title": test_movie1.title}
        )

        serializer1 = MovieListSerializer(test_movie1)
        serializer2 = MovieListSerializer(test_movie2)

        self.assertIn(serializer1.data, response.data)
        self.assertNotIn(serializer2.data, response.data)

    def test_retrieve_movie_detail(self):
        test_movie = sample_movie()
        test_movie.actors.add(Actor.objects.create(
            first_name="test",
            last_name="name"
        ))

        url = detail_url(test_movie.id)
        response = self.client.get(url)

        serializer = MovieDetailSerializer(test_movie)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_create_movie_forbidden(self):
        data = {
            "title": "test_title",
            "description": "test_description",
            "duration": 15,
        }

        response = self.client.post(MOVIE_URL, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieAPITests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@admin.com",
            "qwerty1234",
            is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        data = {
            "title": "test_title",
            "description": "test_description",
            "duration": 15,
        }

        response = self.client.post(MOVIE_URL, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_movie_with_actors_and_genres(self):
        test_actor1 = sample_actor()
        test_actor2 = sample_actor(first_name="Al", last_name="Pacino")

        test_genre1 = sample_genre()
        test_genre2 = sample_genre(name="Action")

        data = {
            "title": "test_title",
            "description": "test_description",
            "duration": 15,
            "actors": [test_actor1.id, test_actor2.id],
            "genres": [test_genre1.id, test_genre2.id]
        }

        response = self.client.post(MOVIE_URL, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_delete_movie_not_allowed(self):
        url = detail_url(sample_movie())
        response = self.client.delete(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED
        )
