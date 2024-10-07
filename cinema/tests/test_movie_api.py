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
        response = self.client.get(MOVIE_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com",
            password="testpassword",
        )
        self.client.force_authenticate(self.user)

    def test_movies_list(self):
        sample_movie()
        movie_with_actors = sample_movie()
        movie_with_genres = sample_movie()

        genre_1 = sample_genre(name="Drama")
        genre_2 = sample_genre(name="Mistery")

        actor_1 = sample_actor(first_name="Daniel", last_name="Deni")
        actor_2 = sample_actor(first_name="John", last_name="Doe")

        movie_with_genres.genres.add(genre_1, genre_2)
        movie_with_actors.actors.add(actor_1, actor_2)

        response = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_filter_movies_by_title(self):
        str_to_search = "test"
        movie_with_no_corresponding_title = sample_movie(title="This is ...")
        movie_with_title_1 = sample_movie(title=f"This is {str_to_search}!")
        movie_with_title_2 = sample_movie(title=f"{str_to_search.upper()}")

        response = self.client.get(MOVIE_URL,{"title": str_to_search})

        serializer_with_no_corresponding_title = MovieListSerializer(
            movie_with_no_corresponding_title
        )
        serializer_with_title_1 = MovieListSerializer(movie_with_title_1)
        serializer_with_title_2 = MovieListSerializer(movie_with_title_2)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(serializer_with_title_1.data,response.data)
        self.assertIn(serializer_with_title_2.data,response.data)
        self.assertNotIn(
            serializer_with_no_corresponding_title.data,
            response.data
        )

    def test_filter_movies_by_genres(self):
        genre_1 = sample_genre(name="Test1")
        genre_2 = sample_genre(name="Test2")

        movie_with_no_genre = sample_movie()
        movie_with_genres_1 = sample_movie()
        movie_with_genres_2 = sample_movie()

        movie_with_genres_1.genres.add(genre_1, genre_2)
        movie_with_genres_2.genres.add(genre_1)

        response = self.client.get(
            MOVIE_URL,
            {"genres": f"{genre_1.id},{genre_2.id}"}
        )

        serializer_with_no_genre = MovieListSerializer(movie_with_no_genre)
        serializer_with_genre_1 = MovieListSerializer(movie_with_genres_1)
        serializer_with_genre_2 = MovieListSerializer(movie_with_genres_2)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(serializer_with_genre_1.data, response.data)
        self.assertIn(serializer_with_genre_2.data, response.data)
        self.assertNotIn(serializer_with_no_genre.data, response.data)

    def test_filter_movies_by_actors(self):
        actor_1 = sample_actor()
        actor_2 = sample_actor()

        movie_without_actors = sample_movie()
        movie_with_actor_1 = sample_movie()
        movie_with_actor_2 = sample_movie()

        movie_with_actor_1.actors.add(actor_1)
        movie_with_actor_2.actors.add(actor_2)

        response = self.client.get(
            MOVIE_URL,
            {"actors": f"{actor_1.id},{actor_2.id}"}
        )

        serializer_without_actor = MovieListSerializer(movie_without_actors)
        serializer_with_actor_1 = MovieListSerializer(movie_with_actor_1)
        serializer_with_actor_2 = MovieListSerializer(movie_with_actor_2)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(serializer_with_actor_1.data, response.data)
        self.assertIn(serializer_with_actor_2.data, response.data)
        self.assertNotIn(serializer_without_actor.data, response.data)

    def test_retrieve_movie(self):
        movie = sample_movie()
        movie.actors.add(sample_actor())
        movie.genres.add(sample_genre())

        response = self.client.get(detail_url(movie.id))

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Test movie",
            "description": "Test description",
            "duration": 90,
        }
        response = self.client.post(MOVIE_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_movie_forbidden(self):
        movie = sample_movie()
        payload = {
            "title": "Update movie",
            "description": "Update description",
            "duration": 90,
        }
        response = self.client.put(detail_url(movie.id), payload)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_partial_update_movie_forbidden(self):
        movie = sample_movie()
        payload = {
            "title": "Update movie",
        }
        response = self.client.patch(detail_url(movie.id), payload)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_movie_forbidden(self):
        movie = sample_movie()
        response = self.client.delete(detail_url(movie.id))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com",
            password="testpassword",
            is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        payload = {
            "title": "Test movie",
            "description": "Test description",
            "duration": 90,
        }
        response = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(id=response.data["id"])

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_create_movie_with_actors_and_genres(self):
        actor_1 = sample_actor()
        actor_2 = sample_actor()

        genre_1 = sample_genre(name="Drama")
        genre_2 = sample_genre(name="Fantasy")

        payload = {
            "title": "Test movie",
            "description": "Test description",
            "duration": 90,
            "actors": [actor_1.id, actor_2.id],
            "genres": [genre_1.id, genre_2.id]
        }
        response = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(id=response.data["id"])
        actors = movie.actors.all()
        genres = movie.genres.all()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn(genre_1, genres)
        self.assertIn(genre_2, genres)
        self.assertEqual(genres.count(), 2)
        self.assertIn(actor_1, actors)
        self.assertIn(actor_2, actors)
        self.assertEqual(actors.count(), 2)

    def test_delete_movie_not_allowed(self):
        movie = sample_movie()
        response = self.client.delete(detail_url(movie.id))

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED
        )
