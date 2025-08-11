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


class UnauthenticatedMovieApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self) -> None:
        payload = {
            "title": "test",
            "description": "test",
            "duration": 20,
        }
        movie = Movie.objects.create(**payload)


        responses = (
            self.client.get(MOVIE_URL),
            self.client.post(MOVIE_URL, payload),
            self.client.get(detail_url(movie.id)),
        )

        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user@test.com", password="test123user"
        )
        self.client.force_authenticate(self.user)

        self.genre = sample_genre()
        self.actor = sample_actor()

        self.movie = sample_movie(title="movie_1")
        self.movie_with_genre = sample_movie(title="movie_2")
        self.movie_with_actor = sample_movie(title="movie_3")
        self.movie_with_genre_and_actor = sample_movie(title="movie_4")

        self.movie_with_genre.genres.add(self.genre)
        self.movie_with_actor.actors.add(self.actor)
        self.movie_with_genre_and_actor.genres.add(self.genre)
        self.movie_with_genre_and_actor.actors.add(self.actor)

        self.serializer_movie = MovieListSerializer(self.movie)
        self.serializer_with_genre = MovieListSerializer(self.movie_with_genre)
        self.serializer_with_actor = MovieListSerializer(self.movie_with_actor)
        self.serializer_with_genre_and_actor = MovieListSerializer(
            self.movie_with_genre_and_actor
        )

    def test_movie_list(self) -> None:
        response = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(serializer.data, response.data)

    def test_filter_movies_by_title(self) -> None:
        response = self.client.get(MOVIE_URL, {"title": f"{self.movie.title}"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(self.serializer_movie.data, response.data)
        self.assertNotIn(self.serializer_with_genre.data, response.data)
        self.assertNotIn(self.serializer_with_actor.data, response.data)
        self.assertNotIn(self.serializer_with_genre_and_actor.data, response.data)

    def test_filter_movies_by_genres(self) -> None:
        response = self.client.get(MOVIE_URL, {"genres": f"{self.genre.id}"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(self.serializer_with_genre.data, response.data)
        self.assertIn(self.serializer_with_genre_and_actor.data, response.data)
        self.assertNotIn(self.serializer_movie.data, response.data)
        self.assertNotIn(self.serializer_with_actor.data, response.data)

    def test_filter_movies_by_actors(self) -> None:
        response = self.client.get(MOVIE_URL, {"actors": f"{self.actor.id}"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(self.serializer_with_actor.data, response.data)
        self.assertIn(self.serializer_with_genre_and_actor.data, response.data)
        self.assertNotIn(self.serializer_movie.data, response.data)
        self.assertNotIn(self.serializer_with_genre.data, response.data)

    def test_movie_retrieve(self) -> None:
        url = detail_url(self.movie_with_genre_and_actor.id)
        response = self.client.get(url)
        serializer = MovieDetailSerializer(self.movie_with_genre_and_actor)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_create_movie_forbidden(self) -> None:
        payload = {
            "title": "test",
            "description": "test",
            "duration": 20,
        }
        response = self.client.post(MOVIE_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.admin = get_user_model().objects.create_user(
            email="admin@user.com", password="test123user", is_staff=True
        )
        self.client.force_authenticate(self.admin)

    def test_create_movie(self) -> None:
        payload = {
            "title": "test",
            "description": "test",
            "duration": 20,
        }
        response = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=response.data["id"])

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        for field in payload:
            self.assertEqual(payload[field], getattr(movie, field))

    def test_create_movie_with_actors_and_genres(self) -> None:
        genre_1 = sample_genre(name="test_1")
        genre_2 = sample_genre(name="test_2")
        actor_1 = sample_actor()
        actor_2 = sample_actor()

        payload = {
            "title": "test",
            "description": "test",
            "duration": 20,
            "genres": [genre_1.id, genre_2.id],
            "actors": [actor_1.id, actor_2.id]
        }

        response = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=response.data["id"])
        genres = movie.genres.all()
        actors = movie.actors.all()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn(genre_1, genres)
        self.assertIn(genre_2, genres)
        self.assertEqual(genres.count(), 2)
        self.assertIn(actor_1, actors)
        self.assertIn(actor_2, actors)
        self.assertEqual(actors.count(), 2)



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
