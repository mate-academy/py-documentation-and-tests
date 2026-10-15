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
    cinema_hall = CinemaHall.objects.create(name="Blue", rows=20, seats_in_row=20)

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

    def test_list_requires_auth(self):
        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_requires_auth(self):
        movie = sample_movie()
        res = self.client.get(detail_url(movie.id))

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "user@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)

    def test_list_movies(self):
        sample_movie(title="B movie")
        sample_movie(title="A movie")

        res = self.client.get(MOVIE_URL)

        movies = Movie.objects.order_by("title")
        serializer = MovieListSerializer(movies, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_title(self):
        movie1 = sample_movie(title="Matrix")
        movie2 = sample_movie(title="Matrix Reloaded")
        movie3 = sample_movie(title="Titanic")

        res = self.client.get(MOVIE_URL, {"title": "matrix"})

        self.assertIn(MovieListSerializer(movie1).data, res.data)
        self.assertIn(MovieListSerializer(movie2).data, res.data)
        self.assertNotIn(MovieListSerializer(movie3).data, res.data)

    def test_filter_movies_by_genres(self):
        genre1 = sample_genre(name="Drama")
        genre2 = sample_genre(name="Comedy")
        movie1 = sample_movie(title="Movie 1")
        movie2 = sample_movie(title="Movie 2")
        movie3 = sample_movie(title="Movie 3")
        movie1.genres.add(genre1)
        movie2.genres.add(genre2)

        res = self.client.get(MOVIE_URL, {"genres": f"{genre1.id},{genre2.id}"})

        self.assertIn(MovieListSerializer(movie1).data, res.data)
        self.assertIn(MovieListSerializer(movie2).data, res.data)
        self.assertNotIn(MovieListSerializer(movie3).data, res.data)

    def test_filter_movies_by_actors(self):
        actor1 = sample_actor(first_name="Brad", last_name="Pitt")
        actor2 = sample_actor(first_name="Tom", last_name="Hanks")
        movie1 = sample_movie(title="Movie 1")
        movie2 = sample_movie(title="Movie 2")
        movie3 = sample_movie(title="Movie 3")
        movie1.actors.add(actor1)
        movie2.actors.add(actor2)

        res = self.client.get(MOVIE_URL, {"actors": f"{actor1.id},{actor2.id}"})

        self.assertIn(MovieListSerializer(movie1).data, res.data)
        self.assertIn(MovieListSerializer(movie2).data, res.data)
        self.assertNotIn(MovieListSerializer(movie3).data, res.data)

    def test_filter_returns_no_duplicates(self):
        genre1 = sample_genre(name="Drama")
        genre2 = sample_genre(name="Comedy")
        movie = sample_movie()
        movie.genres.add(genre1, genre2)

        res = self.client.get(MOVIE_URL, {"genres": f"{genre1.id},{genre2.id}"})

        self.assertEqual(len(res.data), 1)

    def test_combined_filters(self):
        genre = sample_genre()
        actor = sample_actor()
        movie1 = sample_movie(title="Matrix")
        movie2 = sample_movie(title="Titanic")
        movie1.genres.add(genre)
        movie1.actors.add(actor)
        movie2.genres.add(genre)
        movie2.actors.add(actor)

        res = self.client.get(
            MOVIE_URL,
            {"title": "matrix", "genres": str(genre.id), "actors": str(actor.id)},
        )

        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], "Matrix")

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        movie.genres.add(sample_genre())
        movie.actors.add(sample_actor())

        res = self.client.get(detail_url(movie.id))

        serializer = MovieDetailSerializer(movie)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_retrieve_nonexistent_movie_returns_404(self):
        res = self.client.get(detail_url(999))

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_movie_forbidden_for_regular_user(self):
        payload = {
            "title": "New movie",
            "description": "Description",
            "duration": 100,
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Movie.objects.filter(title="New movie").exists())

    def test_upload_image_forbidden_for_regular_user(self):
        movie = sample_movie()

        res = self.client.post(image_upload_url(movie.id), {}, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(self.admin)

    def test_create_movie(self):
        genre = sample_genre()
        actor = sample_actor()
        payload = {
            "title": "New movie",
            "description": "Description",
            "duration": 100,
            "genres": [genre.id],
            "actors": [actor.id],
        }

        res = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(id=res.data["id"])
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(movie.title, payload["title"])
        self.assertIn(genre, movie.genres.all())
        self.assertIn(actor, movie.actors.all())

    def test_create_movie_invalid_payload(self):
        res = self.client.post(MOVIE_URL, {"title": ""})

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_put_and_delete_not_allowed(self):
        movie = sample_movie()

        put_res = self.client.put(detail_url(movie.id), {"title": "X"})
        delete_res = self.client.delete(detail_url(movie.id))

        self.assertEqual(put_res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(delete_res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
