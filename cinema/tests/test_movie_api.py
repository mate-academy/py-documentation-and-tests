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

class UnauthorizedMovieTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

class AuthorizedMovieTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(email="user@test.com", password="testuser")
        self.client.force_authenticate(self.user)

        self.movie = Movie.objects.create(
            title="Titanic",
            description="Description",
            duration=90,
        )

        self.movie.genres.add(sample_genre())
        self.movie.actors.add(sample_actor())

    def test_movie_list(self):

        res = self.client.get(MOVIE_URL)
        items = Movie.objects.all()

        serializer = MovieListSerializer(items, many=True)

        self.assertEqual(serializer.data, res.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_filtered_title(self):

        movie = self.client.get("/api/cinema/movies/?title=nic")
        self.assertEqual(len(movie.data), 1)
        movie = self.client.get("/api/cinema/movies/?title=cin")
        self.assertEqual(len(movie.data), 0)
        self.assertEqual(movie.status_code, status.HTTP_200_OK)

    def test_filtered_genres(self):
        movie_without_genre = sample_movie()
        movie_with_genre_1 = sample_movie(title="Titanic")
        movie_with_genre_2 = sample_movie(title="Cinnamon")

        genres_1 = Genre.objects.create(name="Genre1")
        genres_2 = Genre.objects.create(name="Genre2")

        movie_with_genre_1.genres.add(genres_1)
        movie_with_genre_2.genres.add(genres_2)

        res = self.client.get(
            MOVIE_URL, {"genres": f"{genres_1.id},{genres_2.id}"}
        )

        serializer_without_genre = MovieListSerializer(movie_without_genre)
        serializer_with_genre_1 = MovieListSerializer(movie_with_genre_1)
        serializer_with_genre_2 = MovieListSerializer(movie_with_genre_2)

        self.assertIn(serializer_with_genre_1.data, res.data)
        self.assertIn(serializer_with_genre_2.data, res.data)
        self.assertNotIn(serializer_without_genre, res.data)

    def test_filtered_actors(self):
        movie_without_actor = sample_movie()
        movie_with_actor_1 = sample_movie(title="Titanic")
        movie_with_actor_2 = sample_movie(title="Cinnamon")

        actor_1 = Actor.objects.create(first_name="First", last_name="Last")
        actor_2 = Actor.objects.create(first_name="Second", last_name="Last")

        movie_with_actor_1.actors.add(actor_1)
        movie_with_actor_2.actors.add(actor_2)

        res = self.client.get(
            MOVIE_URL, {"actors": f"{actor_1.id},{actor_2.id}"}
        )

        serializer_without_actor = MovieListSerializer(movie_without_actor)
        serializer_with_actor_1 = MovieListSerializer(movie_with_actor_1)
        serializer_with_actor_2 = MovieListSerializer(movie_with_actor_2)

        self.assertIn(serializer_with_actor_1.data, res.data)
        self.assertIn(serializer_with_actor_2.data, res.data)
        self.assertNotIn(serializer_without_actor.data, res.data)

    def test_retrieve_movie(self):
        movie = sample_movie()
        movie.genres.add(Genre.objects.create(name="Genre4"))
        movie.actors.add(sample_actor())

        url = detail_url(movie.id)

        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_forbidden(self):
        payload = {
            "title": "Titanic",
            "description": "Description",
            "duration": 90,
            "genres": [1],
            "actors": [1,2],
        }
        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

class AdminMovieTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin2@test.com", password="testuser", is_staff=True)
        self.client.force_authenticate(self.user)

    def test_post_movie(self):
        genre = sample_genre()
        actor = sample_actor()
        payload = {
            "title": "Titanic",
            "description": "Description",
            "duration": 90,
            "genres": [genre.id],
            "actors": [actor.id],
        }
        res = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(id=res.data["id"])
        genres = movie.genres.all()
        actors = movie.actors.all()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn(genre, genres)
        self.assertIn(actor, actors)
        self.assertEqual(genres.count(), 1)
        self.assertEqual(actors.count(), 1)

        for key in ["title", "description", "duration"]:
            self.assertEqual(payload[key], getattr(movie, key))
