import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor
from cinema.serializers import MovieSerializer, MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")
MOVIE_SESSION_URL = reverse("cinema:moviesession-list")

movie_data = {
    "title": "Test title",
    "description": "Test description",
    "duration": 90,
}


def sample_movie(**params):
    defaults = movie_data
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
            email="test_user@myproject.com", password="password"
        )
        self.client.force_authenticate(self.user)

    def test_movies_list(self):
        movie = sample_movie()
        movie.actors.add(sample_actor())
        movie.genres.add(sample_genre())

        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.data, serializer.data)

    def test_movies_filtering_by_title(self):
        movie_default = sample_movie()
        custom_title = "Custom title"
        movie_custom = sample_movie(title=custom_title)

        res = self.client.get(MOVIE_URL, {"title": custom_title})

        serializer_default = MovieListSerializer(movie_default)
        serializer_custom = MovieListSerializer(movie_custom)

        self.assertIn(serializer_custom.data, res.data)

        self.assertNotIn(serializer_default.data, res.data)

    def test_movies_filtering_by_genre(self):
        movie_default = sample_movie()
        test_genre_one = sample_genre(name="Test genre one")
        test_genre_two = sample_genre(name="Test genre two")

        movie_with_genre_one = sample_movie(title="Test title one")
        movie_with_genre_two = sample_movie(title="Test title two")
        movie_with_genre_one.genres.add(test_genre_one)
        movie_with_genre_two.genres.add(test_genre_two)

        res = self.client.get(MOVIE_URL, {"genres": test_genre_one.id})

        serializer_default = MovieListSerializer(movie_default)
        serializer_with_genre_one = MovieListSerializer(movie_with_genre_one)
        serializer_with_genre_two = MovieListSerializer(movie_with_genre_two)

        self.assertIn(serializer_with_genre_one.data, res.data)
        self.assertNotIn(serializer_with_genre_two.data, res.data)
        self.assertNotIn(serializer_default.data, res.data)

    def test_movies_filtering_by_actors(self):
        movie_default = sample_movie()
        test_actor_one = sample_actor(first_name="Test", last_name="One")
        test_actor_two = sample_actor(first_name="Test", last_name="Two")

        movie_with_actor_one = sample_movie(title="Test title one")
        movie_with_actor_two = sample_movie(title="Test title two")
        movie_with_actor_one.actors.add(test_actor_one)
        movie_with_actor_two.actors.add(test_actor_two)

        res = self.client.get(MOVIE_URL, {"actors": test_actor_one.id})

        serializer_default = MovieListSerializer(movie_default)
        serializer_with_genre_one = MovieListSerializer(movie_with_actor_one)
        serializer_with_genre_two = MovieListSerializer(movie_with_actor_two)

        self.assertIn(serializer_with_genre_one.data, res.data)
        self.assertNotIn(serializer_with_genre_two.data, res.data)
        self.assertNotIn(serializer_default.data, res.data)

    def test_movie_detail(self):
        movie = sample_movie()
        movie.genres.add(sample_genre())
        movie.actors.add(sample_actor())

        movie = Movie.objects.first()
        serializer = MovieDetailSerializer(movie)

        res = self.client.get(detail_url(movie.id))
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden_for_regular_user(self):
        res = self.client.post(MOVIE_URL, movie_data)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "test_admin@myproject.com", password="password"
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        res = self.client.post(MOVIE_URL, movie_data)

        movie = Movie.objects.first()
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        for key in movie_data:
            self.assertEqual(movie_data[key], getattr(movie, key))

    def test_create_movie_with_actors(self):
        actor_one = sample_actor(first_name="Test", last_name="One")
        actor_two = sample_actor(first_name="Test", last_name="Two")

        movie_with_actors = movie_data.copy()
        movie_with_actors["actors"] = [actor_one.id, actor_two.id]

        res = self.client.post(MOVIE_URL, movie_with_actors)

        movie = Movie.objects.get(id=res.data["id"])
        actors = movie.actors.all()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn(actor_one, actors)
        self.assertIn(actor_two, actors)
        self.assertEqual(actors.count(), 2)

    def test_create_movie_with_genres(self):
        genre_one = sample_genre(name="Genre One")
        genre_two = sample_genre(name="Genre Two")

        movie_with_genres = movie_data.copy()
        movie_with_genres["genres"] = [genre_one.id, genre_two.id]

        res = self.client.post(MOVIE_URL, movie_with_genres)

        movie = Movie.objects.get(id=res.data["id"])
        genres = movie.genres.all()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn(genre_one, genres)
        self.assertIn(genre_two, genres)
        self.assertEqual(genres.count(), 2)
