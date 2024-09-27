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
            url, {"image": "not image"}, format="multipart")

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
        result = self.client.get(MOVIE_URL)
        self.assertEqual(result.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.ua",
            password="testtest"
        )
        self.client.force_authenticate(self.user)

    def test_movie_list(self):
        for _ in range(5):
            sample_movie()

        movie_with_relations = sample_movie()

        actor = sample_actor()
        genre = sample_genre()
        movie_with_relations.actors.add(actor)
        movie_with_relations.genres.add(genre)

        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()

        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_title(self):
        movie1 = sample_movie(title="test_movie1")
        movie2 = sample_movie(title="test_movie2")
        movie3 = sample_movie(title="test_movie3")

        result1 = self.client.get(MOVIE_URL, {"title": "1"})
        result2 = self.client.get(MOVIE_URL, {"title": "test"})

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie3)

        self.assertIn(serializer1.data, result1.data)
        self.assertIn(serializer3.data, result2.data)
        self.assertNotIn(serializer2.data, result1.data)

    def test_filter_movies_by_actors(self):
        movie1 = sample_movie(title="test_movie1")
        movie2 = sample_movie(title="test_movie2")
        movie3 = sample_movie(title="test_movie3")

        actor1 = sample_actor(first_name="vasa")
        actor2 = sample_actor(first_name="alex")

        movie1.actors.add(actor1)
        movie2.actors.add(actor2)

        result1 = self.client.get(
            MOVIE_URL, {"actors": f"{actor1.id}, {actor2.id}"})
        result2 = self.client.get(
            MOVIE_URL, {"actors": f"{actor1.id}"})

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie3)

        self.assertIn(serializer1.data, result2.data)
        self.assertIn(serializer1.data, result1.data)
        self.assertIn(serializer2.data, result1.data)
        self.assertNotIn(serializer3.data, result1.data)
        self.assertNotIn(serializer3.data, result2.data)

    def test_filter_movies_by_genres(self):
        movie1 = sample_movie(title="movie1")
        movie2 = sample_movie(title="movie2")
        movie3 = sample_movie(title="movie3")

        genre1 = sample_genre(name="comedy_test")
        genre2 = sample_genre(name="drama_test")

        movie1.genres.add(genre1)
        movie2.genres.add(genre2)

        result1 = self.client.get(
            MOVIE_URL, {"genres": f"{genre1.id}, {genre2.id}"})
        result2 = self.client.get(
            MOVIE_URL, {"genres": f"{genre1.id}"})

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie3)

        self.assertIn(serializer1.data, result2.data)
        self.assertIn(serializer1.data, result1.data)
        self.assertIn(serializer2.data, result1.data)
        self.assertNotIn(serializer3.data, result1.data)
        self.assertNotIn(serializer3.data, result2.data)

    def test_retrieve_movie(self):
        movie = sample_movie(title="test_movie")

        genre = sample_genre()
        actor = sample_actor()

        movie.genres.add(genre)
        movie.actors.add(actor)

        url = detail_url(movie.id)
        res = self.client.get(url)
        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_for_authorized_user(self):
        payload = {
            "title": "test_m",
            "description": "some desc",
            "duration": 100
        }

        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@test.ua",
            password="testtest",
            is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        payload = {
            "title": "test_m",
            "description": "some desc",
            "duration": 100
        }

        res = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=res.data["id"])
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_create_movie_with_actors_and_genres(self):
        genre1 = sample_genre()
        genre2 = sample_genre(name="drama_test")
        actor1 = sample_actor()
        actor2 = sample_actor(first_name="alex_test")
        payload = {
            "title": "test_m",
            "description": "some desc",
            "duration": 100,
            "genres": [genre1.id, genre2.id],
            "actors": [actor1.id, actor2.id]
        }

        res = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=res.data["id"])
        actors = movie.actors.all()
        genres = movie.genres.all()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        self.assertEqual(actors.count(), 2)
        self.assertEqual(genres.count(), 2)
        self.assertIn(actor1, actors)
        self.assertIn(genre2, genres)

    def test_cant_delete_movie(self):
        movie = sample_movie()

        url = detail_url(movie.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_cant_patch_movie(self):
        movie = sample_movie()
        payload = {"title": "wrong title"}

        url = detail_url(movie.id)
        res = self.client.patch(url, data=payload)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_cant_update_movie(self):
        movie = sample_movie()

        genre1 = sample_genre()
        genre2 = sample_genre(name="drama_test")
        actor1 = sample_actor()
        actor2 = sample_actor(first_name="alex_test")

        payload = {
            "title": "test_movie_update_name",
            "description": "some test descript",
            "duration": 100,
            "genres": [genre1.id, genre2.id],
            "actors": [actor1.id, actor2.id]
        }

        url = detail_url(movie.id)
        res = self.client.put(url, data=payload)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
