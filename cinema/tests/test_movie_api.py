import os
import tempfile

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor
from cinema.serializers import MovieListSerializer

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


class UnauthenticatedMovieApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieFilterApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="TonyStark@test.com", password="TonyStarkHasHeart"
        )
        self.client.force_authenticate(self.user)

        self.movie_with_genre = sample_movie(
            title="test_one", description="test", duration=90
        )
        self.movie_with_actor = sample_movie(
            title="test_two", description="test", duration=90
        )
        self.movie_simple = sample_movie(title="test", description="test", duration=90)

        self.genre_action = sample_genre(name="Action")
        self.actor_one = sample_actor()

        self.movie_with_genre.genres.add(self.genre_action)
        self.movie_with_actor.actors.add(self.actor_one)

    def test_movie_list(self):
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)
        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_movie_filter_by_title(self):
        serializer_title = MovieListSerializer(self.movie_simple)

        res = self.client.get(MOVIE_URL, {"title": f"{self.movie_simple.title}"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer_title.data, res.data)

    def test_movie_filter_by_genre(self):
        serializer_genre = MovieListSerializer(self.movie_with_genre)

        res = self.client.get(MOVIE_URL, {"genres": f"{self.genre_action.id}"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer_genre.data, res.data)

    def test_movie_filter_by_actor(self):
        serializer_actor = MovieListSerializer(self.movie_with_actor)

        res = self.client.get(MOVIE_URL, {"actors": f"{self.actor_one.id}"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer_actor.data, res.data)

    def test_create__movie_forbidden(self):
        payload = {
            "title": "Test",
            "description": "Test",
            "duration": 120,
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="TonyStark@gmail.com", password="TonyStarkHasTheHeart", is_staff=True
        )
        self.client.force_authenticate(self.user)

        self.genre_action = sample_genre(name="Action")
        self.genre_horror = sample_genre(name="Horror")

        self.actor_one = sample_actor()

    def test_create_movie_with_genres_and_actors(self):
        payload = {
            "title": "custom movie",
            "description": "custom description",
            "duration": 180,
            "genres": [self.genre_action.id, self.genre_horror.id],
            "actors": self.actor_one.id,
        }

        res = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=res.data["id"])
        genres = movie.genres.all()
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn(self.genre_horror, genres)
        self.assertIn(self.genre_action, genres)
        self.assertEqual(genres.count(), 2)

    def test_delete_movie_forbidden(self):
        url = detail_url(1)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class MovieSessionTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="TonyStark@gmail.com", password="TonyStarkHasTheHeart", is_staff=True
        )
        self.client.force_authenticate(self.user)
        self.genre = sample_genre()
        self.actor = sample_actor()
        self.movie = sample_movie()
        self.movie.genres.add(self.genre)
        self.movie.actors.add(self.actor)
        self.movie_session = sample_movie_session(movie=self.movie)

    def test_filter_movie_session_by_movie_id(self):
        res = self.client.get(MOVIE_SESSION_URL, {"movie": f"{self.movie.id}"})

        self.assertEqual(res.status_code, 200)
        self.assertIn(self.movie_session.id, [s["id"] for s in res.data])

    def test_filter_movie_session_by_date(self):
        response = self.client.get(MOVIE_SESSION_URL, {"date": "2022-06-02"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.movie_session.id)
