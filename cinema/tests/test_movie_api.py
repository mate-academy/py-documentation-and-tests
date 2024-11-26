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
            email="test@test.test", password="Test1234!", is_staff=False
        )
        self.client.force_authenticate(self.user)

    @classmethod
    def setUpTestData(cls):
        cls.movie = sample_movie()
        cls.actor = sample_actor()
        cls.genre = sample_genre()
        cls.movie_with_actor = sample_movie()
        cls.movie_with_genre = sample_movie()
        cls.movie_with_genre.genres.add(cls.genre)
        cls.movie_with_actor.actors.add(cls.actor)

    def test_movie_list(self):
        sample_movie()
        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)
        self.assertEqual(movies.count(), 4)

    def test_filter_movies_by_actors(self):
        movie = sample_movie()
        movie_with_actor_2 = sample_movie()
        actor_1 = Actor.objects.create(first_name="Jack", last_name="Test")
        actor_2 = Actor.objects.create(first_name="Jane", last_name="Test")

        self.movie_with_actor.actors.add(actor_1)
        movie_with_actor_2.actors.add(actor_2)

        res = self.client.get(
            MOVIE_URL,
            {"actors": f"{actor_1.id},{actor_2.id}"}
        )

        serializer_movie_without_actors = MovieListSerializer(movie)
        serializer_movie_with_actors_1 = MovieListSerializer(self.movie_with_actor)
        serializer_movie_with_actors_2 = MovieListSerializer(movie_with_actor_2)

        self.assertIn(serializer_movie_with_actors_1.data, res.data)
        self.assertIn(serializer_movie_with_actors_2.data, res.data)
        self.assertNotIn(serializer_movie_without_actors, res.data)

    def test_filter_movies_by_genres(self):
        movie = sample_movie()
        movie_with_genre_2 = sample_movie()
        genre_1 = Genre.objects.create(name="Thriller")
        genre_2 = Genre.objects.create(name="Horror")

        self.movie_with_genre.genres.add(genre_1)
        movie_with_genre_2.genres.add(genre_2)

        res = self.client.get(
            MOVIE_URL,
            {"genres": f"{genre_1.id},{genre_2.id}"}
        )

        serializer_movie_without_genres = MovieListSerializer(movie)
        serializer_movie_with_genres_1 = MovieListSerializer(self.movie_with_genre)
        serializer_movie_with_genres_2 = MovieListSerializer(movie_with_genre_2)

        self.assertIn(serializer_movie_with_genres_1.data, res.data)
        self.assertIn(serializer_movie_with_genres_2.data, res.data)
        self.assertNotIn(serializer_movie_without_genres, res.data)

    def test_filter_movies_by_title(self):
        movie = sample_movie(title="Test Title")

        res = self.client.get(MOVIE_URL, {"title": f"{movie.title}"})

        serializer_with_wrong_title = MovieListSerializer(self.movie_with_actor)
        serializer_with_correct_title = MovieListSerializer(movie)

        self.assertIn(serializer_with_correct_title.data, res.data)
        self.assertNotIn(serializer_with_wrong_title, res.data)

    def test_retrieve_movie_detail(self):
        url = detail_url(self.movie.id)

        res = self.client.get(url)

        serializer = MovieDetailSerializer(self.movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {"title": "Gladiator", "description": "Description", "duration": 100}
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@admin.admin", password="Test1234!", is_staff=True
        )
        self.client.force_authenticate(self.user)
        self.actor = sample_actor()
        self.genre = sample_genre()

    def test_create_movie(self):
        payload = {
            "title": "Gladiator",
            "description": "Description",
            "duration": 100,
            "actors": [self.actor.id],
            "genres": [self.genre.id]
        }
        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_delete_movie_not_allowed(self):
        movie = sample_movie()
        url = detail_url(movie.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_update_not_allowed(self):
        movie = sample_movie()
        actor = sample_actor()
        payload = {
            "title": "Updated",
            "actors": [actor.id]
        }
        res = self.client.patch(f"{MOVIE_URL}{movie.id}/", payload)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertNotEqual(movie.title, payload["title"])
