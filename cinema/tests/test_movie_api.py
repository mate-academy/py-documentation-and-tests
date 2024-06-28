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
        res = self.client.post(
            url,
            {"image": "not image"},
            format="multipart"
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


class UnauthorizedMovieApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):

    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com",
            password="test_password"
        )
        self.client.force_authenticate(self.user)

    def test_bus_list(self):
        sample_movie()
        movie_with_actors_genres = Movie.objects.create(
            title="Best of the Best",
            description="Action movie",
            duration=110,
        )
        actors = sample_actor(first_name="Matt", last_name="Damon")
        movie_with_actors_genres.actors.add(actors)
        movie_with_actors_genres.genres.add(sample_genre())
        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_title(self):
        movie_without_filter_title = sample_movie()
        movie_with_filter_title = Movie.objects.create(
            title="Best of the Best",
            description="Action movie",
            duration=110,
        )
        res = self.client.get(
            MOVIE_URL,
            {"title": "best"}
        )
        serializer_movie_without_filter_title = (
            MovieListSerializer(movie_without_filter_title))
        serializer_movie_with_filter_title = (
            MovieListSerializer(movie_with_filter_title))
        self.assertIn(serializer_movie_with_filter_title.data, res.data)
        self.assertNotIn(
            serializer_movie_without_filter_title.data,
            res.data
        )

    def test_filter_movies_by_genres(self):
        movie_without_genres = sample_movie()
        movie_with_genres1 = Movie.objects.create(
            title="Best of the Best",
            description="Action movie",
            duration=110,
        )
        movie_with_genres2_filter = Movie.objects.create(
            title="The Night",
            description="Family's comedy",
            duration=95,
        )
        movie_with_genres1.genres.add(sample_genre(name="French"))
        filter_genre = sample_genre(name="Action")
        movie_with_genres2_filter.genres.add(filter_genre)
        res = self.client.get(
            MOVIE_URL,
            {"genres": {filter_genre.id}}
        )
        serializer_movie_without_genres = (
            MovieListSerializer(movie_without_genres))
        serializer_movie_with_genres1 = (
            MovieListSerializer(movie_with_genres1))
        serializer_movie_with_genres2_filter = (
            MovieListSerializer(movie_with_genres2_filter))
        self.assertIn(serializer_movie_with_genres2_filter.data, res.data)
        self.assertNotIn(serializer_movie_without_genres.data, res.data)
        self.assertNotIn(serializer_movie_with_genres1.data, res.data)

    def test_filter_movies_by_actors(self):
        movie_without_actors = sample_movie()
        movie_with_actor1 = Movie.objects.create(
            title="Best of the Best",
            description="Action movie",
            duration=110,
        )
        movie_with_actor2_filter = Movie.objects.create(
            title="The Night",
            description="Family's comedy",
            duration=95,
        )
        movie_with_actor1.actors.add(
            sample_actor(first_name="Jack", last_name="Nicholson"))
        filter_actor = sample_actor(first_name="Tom", last_name="Hanks")
        movie_with_actor2_filter.actors.add(filter_actor)
        res = self.client.get(
            MOVIE_URL,
            {"actors": {filter_actor.id}}
        )
        serializer_movie_without_actors = (
            MovieListSerializer(movie_without_actors))
        serializer_movie_with_actor1 = (
            MovieListSerializer(movie_with_actor1))
        serializer_movie_with_actor2_filter = (
            MovieListSerializer(movie_with_actor2_filter))
        self.assertIn(serializer_movie_with_actor2_filter.data, res.data)
        self.assertNotIn(serializer_movie_without_actors.data, res.data)
        self.assertNotIn(serializer_movie_with_actor1.data, res.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        movie.actors.add(sample_actor())
        movie.genres.add(sample_genre())
        url = detail_url(movie.id)
        res = self.client.get(url)
        serializer = MovieDetailSerializer(movie)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_bus_forbidden(self):
        payload = {
            "title": "Sample movie",
            "description": "Sample description",
            "duration": 90,
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTests(TestCase):

    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com",
            password="test_password",
            is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        genre = sample_genre()
        actor = sample_actor()
        payload = {
            "title": "Sample movie",
            "description": "Sample description",
            "duration": 90,
            "genres": [genre.id],
            "actors": [actor.id]
        }
        res = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=res.data["id"])
        genres = movie.genres.all()
        actors = movie.actors.all()
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn(genre, genres)
        self.assertIn(genre, genres)
        self.assertIn(actor, actors)
        self.assertEqual(genres.count(), 1)
        self.assertEqual(actors.count(), 1)
        for key in ["title", "description", "duration"]:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_delete_movie_not_allowed(self):
        movie = sample_movie()
        url = detail_url(movie.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
