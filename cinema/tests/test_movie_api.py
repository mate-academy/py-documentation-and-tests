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
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.test", password="test_password"
        )
        self.client.force_authenticate(user=self.user)

    def test_movies_list(self):
        movie = sample_movie(title="The Matrix")
        movie.genres.add(sample_genre())
        movie.actors.add(sample_actor())
        sample_movie(title="Avatar")

        res = self.client.get(MOVIE_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_retrieve_movie(self):
        movie = sample_movie()
        movie.genres.add(sample_genre())
        movie.actors.add(sample_actor())

        res = self.client.get(detail_url(movie.id))
        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_title(self):
        movie1 = sample_movie(title="The Matrix")
        movie2 = sample_movie(title="Matrix Reloaded")
        sample_movie(title="Titanic")

        res = self.client.get(MOVIE_URL, {"title": "Matrix"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertCountEqual(
            [movie["id"] for movie in res.data],
            [movie1.id, movie2.id],
        )

    def test_filter_movies_by_genres(self):
        genre1 = sample_genre(name="Drama")
        genre2 = sample_genre(name="Comedy")
        other_genre = sample_genre(name="Horror")

        movie1 = sample_movie(title="Movie 1")
        movie1.genres.add(genre1)

        movie2 = sample_movie(title="Movie 2")
        movie2.genres.add(genre2)

        movie3 = sample_movie(title="Movie 3")
        movie3.genres.add(other_genre)

        res = self.client.get(
            MOVIE_URL,
            {"genres": f"{genre1.id},{genre2.id}"},
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertCountEqual(
            [movie["id"] for movie in res.data],
            [movie1.id, movie2.id],
        )

    def test_filter_movies_by_actors(self):
        actor1 = sample_actor(first_name="George", last_name="Clooney")
        actor2 = sample_actor(first_name="Brad", last_name="Pitt")
        other_actor = sample_actor(first_name="Tom", last_name="Hanks")

        movie1 = sample_movie(title="Movie 1")
        movie1.actors.add(actor1)

        movie2 = sample_movie(title="Movie 2")
        movie2.actors.add(actor2)

        movie3 = sample_movie(title="Movie 3")
        movie3.actors.add(other_actor)

        res = self.client.get(
            MOVIE_URL,
            {"actors": f"{actor1.id},{actor2.id}"},
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertCountEqual(
            [movie["id"] for movie in res.data],
            [movie1.id, movie2.id],
        )

    def test_filter_movies_by_title_genre_and_actor(self):
        genre = sample_genre()
        actor = sample_actor()

        matching_movie = sample_movie(title="The Matrix")
        matching_movie.genres.add(genre)
        matching_movie.actors.add(actor)

        wrong_title = sample_movie(title="Titanic")
        wrong_title.genres.add(genre)
        wrong_title.actors.add(actor)

        wrong_genre = sample_movie(title="Matrix Reloaded")
        wrong_genre.actors.add(actor)

        wrong_actor = sample_movie(title="Matrix Revolutions")
        wrong_actor.genres.add(genre)

        res = self.client.get(
            MOVIE_URL,
            {
                "title": "matrix",
                "genres": str(genre.id),
                "actors": str(actor.id),
            },
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [movie["id"] for movie in res.data],
            [matching_movie.id],
        )

    def test_create_movie_forbidden(self):
        genre = sample_genre()
        actor = sample_actor()
        payload = {
            "title": "New movie",
            "description": "Movie description",
            "duration": 120,
            "genres": [genre.id],
            "actors": [actor.id],
        }

        response = self.client.post(
            MOVIE_URL,
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Movie.objects.count(), 0)


class AdminMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@example.com",
            password="testpass123",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.user)

        self.genre = sample_genre()
        self.actor = sample_actor()

        self.payload = {
            "title": "New movie",
            "description": "Movie description",
            "duration": 120,
            "genres": [self.genre.id],
            "actors": [self.actor.id],
        }

    def test_create_movie(self):
        res = self.client.post(
            MOVIE_URL,
            self.payload,
            format="json",
        )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Movie.objects.count(), 1)

        movie = Movie.objects.get(id=res.data["id"])

        self.assertEqual(movie.title, self.payload["title"])
        self.assertEqual(movie.description, self.payload["description"])
        self.assertEqual(movie.duration, self.payload["duration"])

        self.assertCountEqual(
            movie.genres.values_list("id", flat=True),
            self.payload["genres"],
        )
        self.assertCountEqual(
            movie.actors.values_list("id", flat=True),
            self.payload["actors"],
        )

    def test_create_movie_with_multiple_genres_and_actors(self):
        genre2 = sample_genre(name="Comedy")
        actor2 = sample_actor(first_name="Brad", last_name="Pitt")

        payload = {
            **self.payload,
            "genres": [self.genre.id, genre2.id],
            "actors": [self.actor.id, actor2.id],
        }

        res = self.client.post(
            MOVIE_URL,
            payload,
            format="json",
        )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Movie.objects.count(), 1)

        movie = Movie.objects.get(id=res.data["id"])

        self.assertCountEqual(
            movie.genres.values_list("id", flat=True),
            payload["genres"],
        )
        self.assertCountEqual(
            movie.actors.values_list("id", flat=True),
            payload["actors"],
        )

    def test_update_and_delete_movie_not_allowed(self):
        movie = sample_movie()
        original_title = movie.title
        url = detail_url(movie.id)

        for method in ("put", "patch", "delete"):
            with self.subTest(method=method):
                res = getattr(self.client, method)(
                    url,
                    self.payload,
                    format="json",
                )

                self.assertEqual(
                    res.status_code,
                    status.HTTP_405_METHOD_NOT_ALLOWED,
                )
                self.assertTrue(
                    Movie.objects.filter(id=movie.id).exists()
                )
                movie.refresh_from_db()
                self.assertEqual(movie.title, original_title)

