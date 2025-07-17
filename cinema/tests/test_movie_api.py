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
            email="admin@myproject.com", password="password"
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
        response = self.client.get(MOVIE_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com",
            password="test123",
        )

        self.client.force_authenticate(user=self.user)

    def test_movies_list(self):
        sample_movie()
        movie_test = sample_movie()
        movie_test.genres.add(sample_genre())
        movie_test.actors.add(sample_actor())

        response = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"], serializer.data)

    def test_filter_movies_by_genre(self):
        movie_without_genres = sample_movie()
        movie_with_genre1 = sample_movie(title="Terminator 2")
        movie_with_genre2 = sample_movie(title="Inception")


        genre1 = Genre.objects.create(name="Action")
        genre2 = Genre.objects.create(name="Sci-Fi")

        movie_with_genre1.genres.add(genre1)
        movie_with_genre2.genres.add(genre2)

        response = self.client.get(
            MOVIE_URL,
            {"genres": f"{genre1.id},{genre2.id}"},
        )

        serializer_without_genres = MovieListSerializer(movie_without_genres)
        serializer_movie_genre1 = MovieListSerializer(movie_with_genre1)
        serializer_movie_genre2= MovieListSerializer(movie_with_genre2)

        self.assertIn(serializer_movie_genre1.data, response.data["results"])
        self.assertIn(serializer_movie_genre2.data, response.data["results"])
        self.assertNotIn(serializer_without_genres.data, response.data["results"])

    def test_filter_movies_by_actors(self):
        movie_without_actors = sample_movie()
        movie_with_actor1 = sample_movie(title="Terminator 2")
        movie_with_actor2 = sample_movie(title="Inception")


        actor1 = Actor.objects.create(first_name="Arnold", last_name="Schwarzenegger")
        actor2 = Actor.objects.create(first_name="Leonardo", last_name="Dicaprio")

        movie_with_actor1.actors.add(actor1)
        movie_with_actor2.actors.add(actor2)

        response = self.client.get(
            MOVIE_URL,
            {"actors": f"{actor1.id},{actor2.id}"},
        )

        serializer_without_actors = MovieListSerializer(movie_without_actors)
        serializer_movie_actor1 = MovieListSerializer(movie_with_actor1)
        serializer_movie_actor2 = MovieListSerializer(movie_with_actor2)

        self.assertIn(serializer_movie_actor1.data, response.data["results"])
        self.assertIn(serializer_movie_actor2.data, response.data["results"])
        self.assertNotIn(serializer_without_actors.data, response.data["results"])


    def test_retrieve_movie_details(self):
        movie = sample_movie()
        movie.genres.add(sample_genre())
        movie.actors.add(sample_actor())

        url = detail_url(movie.id)

        response = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Terminator 2",
            "description": "Movie about terminator",
            "duration": 150,
            "genres": [sample_genre().id],
            "actors": [sample_actor().id],
        }

        response = self.client.post(MOVIE_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com", password="test123", is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        genre1 = Genre.objects.create(name="Action")
        actor1 = Actor.objects.create(first_name="Arnold", last_name="Schwarzenegger")

        payload = {
            "title": "Terminator 2",
            "description": "Movie about terminator",
            "duration": 150,
            "genres": [genre1.id],
            "actors": [actor1.id],
        }

        response = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(id=response.data["id"])
        genres = movie.genres.all()
        actors = movie.actors.all()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn(genre1, genres)
        self.assertIn(actor1, actors)
        self.assertEqual(genres.count(), 1)
        self.assertEqual(actors.count(), 1)
