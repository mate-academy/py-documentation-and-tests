import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor
from cinema.serializers import (
    MovieSerializer,
    MovieListSerializer,
    MovieDetailSerializer,
)

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
        name="Blue",
        rows=20,
        seats_in_row=20
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


class UnauthenticatedMovieAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com", password="test_password"
        )
        self.client.force_authenticate(self.user)

    def test_movie_list(self):
        sample_movie()

        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.data, serializer.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_movie_filter_by_title(self):
        sample_movie(title="King")
        sample_movie(title="Queen", description="Good movie")
        sample_movie()

        movie_queen = Movie.objects.filter(title="Queen")
        res = self.client.get(MOVIE_URL, {"title": "Que"})
        serializer = MovieListSerializer(movie_queen, many=True)

        self.assertEqual(res.data, serializer.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_movie_filter_by_genres(self):
        poem_genre = sample_genre(name="Poem")
        drama_genre = sample_genre(name="Drama")

        poem_movie = sample_movie()
        drama_movie = sample_movie()
        simple_movie = sample_movie()

        poem_movie.genres.add(poem_genre)
        drama_movie.genres.add(drama_genre)

        res = self.client.get(
            MOVIE_URL, {"genres": f"{poem_genre.id},{drama_genre.id}"}
        )

        serializer_poem_movie = MovieListSerializer(poem_movie)
        serializer_drama_movie = MovieListSerializer(drama_movie)
        serializer_simple_movie = MovieListSerializer(simple_movie)

        self.assertIn(serializer_poem_movie.data, res.data)
        self.assertIn(serializer_drama_movie.data, res.data)
        self.assertNotIn(serializer_simple_movie.data, res.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_movie_filter_by_actors(self):
        timmy_actor = sample_actor(first_name="Timmy", last_name="Clooney")
        joe_actor = sample_actor(first_name="Joe", last_name="Leono")

        movie_with_timmy = sample_movie()
        movie_with_joe = sample_movie()
        simple_movie = sample_movie()

        movie_with_timmy.actors.add(timmy_actor)
        movie_with_joe.actors.add(joe_actor)

        res = self.client.get(
            MOVIE_URL,
            {"actors": f"{timmy_actor.id},{joe_actor.id}"}
        )

        serializer_movie_with_timmy = MovieListSerializer(movie_with_timmy)
        serializer_movie_with_joe = MovieListSerializer(movie_with_joe)
        serializer_simple_movie = MovieListSerializer(simple_movie)

        self.assertIn(serializer_movie_with_timmy.data, res.data)
        self.assertIn(serializer_movie_with_joe.data, res.data)
        self.assertNotIn(serializer_simple_movie.data, res.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_movie_retrieve(self):
        movie = sample_movie()
        movie.genres.add(sample_genre())
        movie.actors.add(sample_actor())

        url = detail_url(movie.id)
        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.data, serializer.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_movie_create(self):

        payload = {
            "title": "Try Create Movie",
            "description": "try",
            "duration": 90,
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(Movie.objects.count(), 0)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@test.com", password="test_password", is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_movie_create(self):

        actor_1 = sample_actor(first_name="George", last_name="Clooney")
        actor_2 = sample_actor(first_name="Loe", last_name="Dee")
        genre = sample_genre()

        payload = {
            "title": "Try Create Movie",
            "description": "try",
            "duration": 90,
            "actors": [actor_1.id, actor_2.id],
            "genres": genre.id,
        }

        res = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=res.data["id"])
        actors = movie.actors.all()

        self.assertEqual(Movie.objects.count(), 1)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(actors.count(), 2)

    def test_movie_delete_not_allowed(self):
        movie = sample_movie()
        url = detail_url(movie.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_movie_update_not_allowed(self):
        movie = sample_movie()
        url = detail_url(movie.id)
        res = self.client.patch(url, {"title": "Try Updated Movie"})

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
