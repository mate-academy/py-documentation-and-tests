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


class UnauthenticatedMovieApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(MOVIE_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@test.com", "password"
        )
        self.client.force_authenticate(self.user)
        self.movie1 = sample_movie(title="first")
        self.movie2 = sample_movie(title="second")
        self.movie3 = sample_movie(title="third")

    def test_movie_list(self):
        genre1 = sample_genre(name="first")
        actor1 = sample_actor(first_name="actor1", last_name="test1")
        self.movie1.genres.add(genre1)
        self.movie2.actors.add(actor1)

        response = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_movie_detail(self):
        genre = sample_genre()
        actor = sample_actor()
        self.movie1.genres.add(genre)
        self.movie1.actors.add(actor)
        url = detail_url(self.movie1.id)
        response = self.client.get(url)
        serializer = MovieDetailSerializer(self.movie1)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)
        self.assertIn("genres", response.data)
        self.assertIn("actors", response.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "test movie",
            "description": "test description",
            "duration": 100,
        }
        response = self.client.post(MOVIE_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_filter_by_genres(self):
        genre1 = sample_genre(name="test")
        genre2 = sample_genre(name="TEST_2")
        genre3 = sample_genre(name="genre")

        self.movie1.genres.add(genre1)
        self.movie2.genres.add(genre1, genre2)
        self.movie3.genres.add(genre3)

        response = self.client.get(MOVIE_URL, {"genres": f"{genre1.id}, {genre2.id}"})

        serializer1 = MovieListSerializer(self.movie1)
        serializer2 = MovieListSerializer(self.movie2)
        serializer3 = MovieListSerializer(self.movie3)

        self.assertIn(serializer1.data, response.data)
        self.assertIn(serializer2.data, response.data)
        self.assertNotIn(serializer3.data, response.data)

    def test_filter_by_actors(self):
        actor1 = sample_actor(first_name="actor1", last_name="test1")
        actor2 = sample_actor(first_name="actor2", last_name="test2")
        actor3 = sample_actor(first_name="firstname", last_name="lastname")

        self.movie1.actors.add(actor1)
        self.movie2.actors.add(actor1, actor2)
        self.movie3.actors.add(actor3)

        response = self.client.get(MOVIE_URL, {"actors": f"{actor1.id}, {actor2.id}"})

        serializer1 = MovieListSerializer(self.movie1)
        serializer2 = MovieListSerializer(self.movie2)
        serializer3 = MovieListSerializer(self.movie3)

        self.assertIn(serializer1.data, response.data)
        self.assertIn(serializer2.data, response.data)
        self.assertNotIn(serializer3.data, response.data)

    def test_filter_by_title(self):
        response = self.client.get(MOVIE_URL, {"title": "iR"})

        serializer1 = MovieListSerializer(self.movie1)
        serializer2 = MovieListSerializer(self.movie2)
        serializer3 = MovieListSerializer(self.movie3)

        self.assertIn(serializer1.data, response.data)
        self.assertIn(serializer3.data, response.data)
        self.assertNotIn(serializer2.data, response.data)


class AdminMovieApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@admin.com", "password", is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_movie_allowed(self):
        payload = {
            "title": "test movie",
            "description": "test description",
            "duration": 100,
        }
        response = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=response.data["id"])
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_create_movie_with_genres_and_actors(self):
        genre1 = sample_genre(name="genre_test1")
        genre2 = sample_genre(name="genre_test2")
        actor1 = sample_actor(first_name="first", last_name="last")
        actor2 = sample_actor(first_name="first2", last_name="last2")
        payload = {
            "title": "test movie",
            "description": "test description",
            "duration": 100,
            "genres": [genre1.id, genre2.id],
            "actors": [actor1.id, actor2.id]
        }
        response = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=response.data["id"])
        genres = movie.genres.all()
        actors = movie.actors.all()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn(genre1, genres)
        self.assertIn(genre2, genres)
        self.assertIn(actor1, actors)
        self.assertIn(actor2, actors)
