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


def detail_movie_url(id: int):
    return reverse("cinema:movie-detail", args=(id,))

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
            password="test1234"
        )
        self.client.force_authenticate(self.user)

    def test_movie_list(self):
        sample_movie()

        response = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(response.data, serializer.data)

    def test_filter_movies_by_actors(self):
        sample_movie()
        first_actor = sample_actor(
            first_name="Keanu",
            last_name="Reeves"
        )
        second_actor = sample_actor(
            first_name="Leonardo",
            last_name="Dicaprio"
        )
        movie_with_actors_1 = sample_movie(
            title="test_title_1",
            description="test_description_1",
            duration=100,
        )
        movie_with_actors_2 = sample_movie(
            title="test_title_2",
            description="test_description_2",
            duration=120,
        )
        movie_with_actors_1.actors.add(first_actor)
        movie_with_actors_2.actors.add(second_actor)
        response = self.client.get(
            MOVIE_URL,
            {"actors": f"{first_actor.id},{second_actor.id}"}
        )
        movies = Movie.objects.filter(actors__id__in=[first_actor.id, second_actor.id])
        serializer = MovieListSerializer(movies, many=True)
        self.assertEqual(response.data, serializer.data)

    def test_filter_movies_by_genres(self):
        sample_movie()
        first_genre = sample_genre(
            name="drama"
        )
        second_genre = sample_genre(
            name="crime"
        )
        movie_with_genres_1 = sample_movie(
            title="test_title_1",
            description="test_description_1",
            duration=100,
        )
        movie_with_genres_2 = sample_movie(
            title="test_title_2",
            description="test_description_2",
            duration=120,
        )
        movie_with_genres_1.genres.add(first_genre)
        movie_with_genres_2.genres.add(second_genre)
        response = self.client.get(
            MOVIE_URL,
            {"genres": f"{first_genre.id},{second_genre.id}"}
        )
        movies = Movie.objects.filter(genres__id__in=[first_genre.id, second_genre.id])
        serializer = MovieListSerializer(movies, many=True)
        self.assertEqual(response.data, serializer.data)

    def test_filter_movies_by_title(self):
        sample_movie(
            title="harry potter",
            description="description harry potter",
            duration=100
        )
        sample_movie(
            title="bad_boys",
            description="description bad boys",
            duration=120
        )

        response = self.client.get(
            MOVIE_URL,
            {"title": "harry"}
        )
        movies = Movie.objects.filter(title__icontains="harry")
        serializer = MovieListSerializer(movies, many=True)
        self.assertEqual(response.data, serializer.data)

    def test_retrieve_movie(self):
        movie = sample_movie()
        movie.actors.add(
            Actor.objects.create(
                first_name="Leonardo",
                last_name="Dicaprio"
            )
        )
        movie.genres.add(
            Genre.objects.create(
                name="action"
            )
        )
        url = detail_movie_url(movie.id)
        serializer = MovieDetailSerializer(movie)
        response = self.client.get(url)
        self.assertEqual(response.data, serializer.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_movie_forbidden(self):
        movie = {
            "title": "Sample movie",
            "description": "Sample description",
            "duration": 90,
        }

        response = self.client.post(MOVIE_URL, movie)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = get_user_model().objects.create_superuser(
            email="admin@test.com",
            password="test1234"
        )
        self.client.force_authenticate(self.admin)

    def test_create_movie(self):
        payload = {
            "title": "Sample movie",
            "description": "Sample description",
            "duration": 90,
        }

        response = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=response.data["id"])

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_create_movie_with_actors_and_genres(self):
        first_actor = Actor.objects.create(
            first_name="Keanu",
            last_name="Reeves"
        )
        second_actor = Actor.objects.create(
            first_name="Leonardo",
            last_name="Dicaprio"
        )
        first_genre = Genre.objects.create(
            name="drama"
        )
        second_genre = Genre.objects.create(
            name="action"
        )
        payload = {
            "title": "Sample movie",
            "description": "Sample description",
            "duration": 90,
            "genres": [first_genre.id, second_genre.id],
            "actors": [first_actor.id, second_actor.id]
        }
        response = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=response.data["id"])
        genres = movie.genres.all()
        actors = movie.actors.all()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn(first_actor, actors)
        self.assertIn(second_actor, actors)
        self.assertIn(first_genre, genres)
        self.assertIn(second_genre, genres)
        self.assertEqual(genres.count(), 2)
        self.assertEqual(actors.count(), 2)

    def test_delete_movie_not_allowed(self):
        movie = sample_movie()
        url = detail_movie_url(movie.id)
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
