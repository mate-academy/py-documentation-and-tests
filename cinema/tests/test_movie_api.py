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

class UnauthenticatedMovieTests(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        result = self.client.get(MOVIE_URL)
        self.assertEqual(result.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@test.com",
            password="admin1222"
        )
        self.client.force_authenticate(self.user)

    def test_filter_movies_by_genres(self):
        movie_without_genres = sample_movie()
        movie_with_genre_1 = sample_movie()
        movie_with_genre_2 = sample_movie()
        movie_with_genre_3 = sample_movie()

        genre_1 = sample_genre(name="comedy")
        genre_2 = sample_genre(name="sci-fi")
        genre_3 = sample_genre(name="fantastic")

        movie_with_genre_1.genres.add(genre_1)
        movie_with_genre_2.genres.add(genre_2)
        movie_with_genre_3.genres.add(genre_3)

        result = self.client.get(
            MOVIE_URL, {"genres": f"{genre_1.id}, {genre_2.id}, {genre_3.id}"}
        )

        serializer_without_genres = MovieListSerializer(movie_without_genres)
        serializer_with_genre_1 = MovieListSerializer(movie_with_genre_1)
        serializer_with_genre_2 = MovieListSerializer(movie_with_genre_2)
        serializer_with_genre_3 = MovieListSerializer(movie_with_genre_3)

        self.assertNotIn(serializer_without_genres.data, result.data)
        self.assertIn(serializer_with_genre_1.data, result.data)
        self.assertIn(serializer_with_genre_2.data, result.data)
        self.assertIn(serializer_with_genre_3.data, result.data)

    def test_filter_movies_by_actors(self):
        movie_without_actors = sample_movie()
        movie_with_actor_1 = sample_movie()
        movie_with_actor_2 = sample_movie()

        actor_1 = sample_actor(first_name="Jared", last_name="Leto")
        actor_2 = sample_actor(first_name="Emma", last_name="Stone")

        movie_with_actor_1.actors.add(actor_1)
        movie_with_actor_2.actors.add(actor_2)

        result = self.client.get(
            MOVIE_URL, {"actors": f"{actor_1.id}, {actor_2.id}"}
        )

        serializer_without_actors = MovieListSerializer(movie_without_actors)
        serializer_with_actor_1 = MovieListSerializer(movie_with_actor_1)
        serializer_with_actor_2 = MovieListSerializer(movie_with_actor_2)

        self.assertNotIn(serializer_without_actors.data, result.data)
        self.assertIn(serializer_with_actor_1.data, result.data)
        self.assertIn(serializer_with_actor_2.data, result.data)

    def test_filter_movies_by_title(self):
        movie_1 = sample_movie(title="Oppenheimer")
        movie_2 = sample_movie(title="Fire and Water")

        result = self.client.get(
            MOVIE_URL, {"title": "Oppenheimer"}
        )

        serializer_movie_1 = MovieListSerializer(movie_1)
        serializer_movie_2 = MovieListSerializer(movie_2)

        self.assertIn(serializer_movie_1.data, result.data)
        self.assertNotIn(serializer_movie_2.data, result.data)

    def test_patch_movie_detail(self):
        movie = sample_movie()
        movie.actors.add(sample_actor())
        movie.genres.add(sample_genre())
        url = detail_url(movie.id)
        result = self.client.get(url)
        serializer = MovieDetailSerializer(movie)

        self.assertEqual(result.status_code, status.HTTP_200_OK)
        self.assertEqual(result.data, serializer.data)


class AdminMovieTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="superpuperadmin@test.com",
            password="password1",
            is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_delete_movie_not_allowed(self):
        movie = sample_movie()
        url = detail_url(movie.id)
        result = self.client.delete(url)
        self.assertEqual(
            result.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def test_update_movie_partially_not_allowed(self):
        movie = sample_movie()
        payload = {
            "title": "Title",
        }
        url = detail_url(movie.id)
        res = self.client.patch(url, payload)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_create_movie_with_actor_and_genre(self):
        actor = sample_actor()
        genre = sample_genre()

        payload = {
            "title": "Poor Things",
            "description": "Movie with Emma Stone",
            "duration": 180,
            "actors": actor.id,
            "genres": genre.id

        }

        result = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=result.data["id"])
        genres = movie.genres.all()
        actors = movie.actors.all()

        self.assertEqual(result.status_code, status.HTTP_201_CREATED)

        self.assertIn(actor, actors)
        self.assertIn(genre, genres)

        self.assertEqual(genres.count(), 1)
        self.assertEqual(actors.count(), 1)

    def test_update_movie_not_allowed(self):
        movie = sample_movie()
        payload = {"title": "Title", "description": "description"}
        url = detail_url(movie.id)
        res = self.client.put(url, payload)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)