import os
import tempfile

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

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
            email="test@test@gmail.com",
            password="password_test"
        )
        self.client.force_authenticate(self.user)

    def test_movie_list(self):
        sample_movie()
        movie_with_genres_actors = sample_movie()

        genre = sample_genre()
        actor = sample_actor()

        movie_with_genres_actors.genres.add(genre)
        movie_with_genres_actors.actors.add(actor)

        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.data, serializer.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_filter_by_actors(self):
        movie_without_genre_actor = sample_movie()
        movie_with_genre_1_2 = sample_movie(title="Inception123")
        movie_with_genre_3 = sample_movie(title="Inception456")
        movie_with_actor_1 = sample_movie(title="Inception789")
        movie_with_actor_2 = sample_movie(title="Inception101")
        movie_with_another_title = sample_movie(title="Inception_test)))")

        genre_1 = sample_genre(name="genre_1_test")
        genre_2 = sample_genre(name="genre_2_test")
        genre_3 = sample_genre(name="genre_3_test")

        actor_1 = sample_actor()
        actor_2 = sample_actor()

        movie_with_genre_1_2.genres.add(genre_1, genre_2)
        movie_with_genre_3.genres.add(genre_3)
        movie_with_actor_1.actors.add(actor_1)
        movie_with_actor_2.actors.add(actor_2)



        res_genres = self.client.get(
            MOVIE_URL,
            {
                "genres": f"{genre_1.id},{genre_2.id}"
            }
        )
        res_actors = self.client.get(
            MOVIE_URL,
            {
                "actors": f"{actor_1.id}"
            }
        )
        res_title = self.client.get(
            MOVIE_URL,
            {
                "title": "Inception_test)))"
            }
        )

        serializer_without_actors_genres = MovieListSerializer(
            movie_without_genre_actor
        )
        serializer_with_genres = MovieListSerializer(
            movie_with_genre_1_2
        )
        serializer_with_another_genre = MovieListSerializer(
            movie_with_genre_3
        )
        serializer_with_actors = MovieListSerializer(
            movie_with_actor_1
        )
        serializer_with_another_actor = MovieListSerializer(
            movie_with_actor_2
        )
        serializer_with_custom_title = MovieListSerializer(
            movie_with_another_title
        )

        self.assertNotIn(serializer_without_actors_genres.data, res_actors.data)
        self.assertNotIn(serializer_without_actors_genres.data, res_genres.data)
        self.assertNotIn(serializer_with_custom_title.data, res_genres.data)
        self.assertNotIn(serializer_with_custom_title.data, res_actors.data)
        self.assertNotIn(serializer_with_another_actor, res_actors.data)
        self.assertNotIn(serializer_with_another_genre.data, res_genres.data)

        self.assertNotIn(serializer_with_actors.data, res_genres.data)
        self.assertNotIn(serializer_with_genres.data, res_actors.data)

        self.assertIn(serializer_with_genres.data, res_genres.data)
        self.assertIn(serializer_with_actors.data, res_actors.data)
        self.assertIn(serializer_with_custom_title.data, res_title.data)

        self.assertEqual(res_actors.status_code, status.HTTP_200_OK)
        self.assertEqual(res_genres.status_code, status.HTTP_200_OK)
        self.assertEqual(res_title.status_code, status.HTTP_200_OK)

    def test_retrieve_movie(self):
        movie = sample_movie()
        movie.actors.add(sample_actor())
        movie.genres.add(sample_genre())

        res = self.client.get(
            detail_url(movie.id)
        )

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.data, serializer.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Inception xD",
            "description": "test_description",
            "duration": 99
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@admin.test",
            password="testpassword",
            is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        payload = {
            "title": "NotInception",
            "description": "some_test_description",
            "duration": 98,
        }

        res = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_create_movie_with_actors_genres(self):
        actor = sample_actor()
        genre = sample_genre()
        payload = {
            "title": "SomeInception",
            "description": "some_test_description",
            "duration": 97,
            "actors": [actor.id],
            "genres": [genre.id]
        }

        res = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=res.data["id"])
        actors = movie.actors.all()
        genres = movie.genres.all()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn(actor, actors)
        self.assertIn(genre, genres)

    def test_delete_movie_not_allowed(self):
        movie = sample_movie()

        res = self.client.delete(detail_url(movie.id))

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
