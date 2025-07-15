import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor

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


class UnauthorizedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthorizedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="testuser@mail.com",
            password="testpassword",
        )
        self.client.force_authenticate(self.user)

    def test_list_movies(self):
        sample_movie()
        movie_with_actors_and_genres = sample_movie(
            title="The Departed",
            description="Sample description ",
            duration=100
        )

        genre_1 = sample_genre()
        genre_2 = sample_genre(name="Crime")

        actor_1 = sample_actor()
        actor_2 = sample_actor(
            first_name="Leonardo",
            last_name="DiCaprio"
        )

        movie_with_actors_and_genres.genres.add(
            genre_1, genre_2
        )
        movie_with_actors_and_genres.actors.add(
            actor_1, actor_2
        )

        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_by_title(self):
        movie_1 = sample_movie()
        movie_2 = sample_movie(
            title="The Departed",
            description="Sample description",
            duration=100
        )
        movie_3 = sample_movie(
            title="Unbreakable",
            description="Sample description",
            duration=120
        )

        res = self.client.get(MOVIE_URL, {"title": f"{movie_1.title}"})

        serializer_movie_1 = MovieListSerializer(movie_1)
        serializer_movie_2 = MovieListSerializer(movie_2)
        serializer_movie_3 = MovieListSerializer(movie_3)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer_movie_1.data, res.data)
        self.assertNotIn(serializer_movie_2.data, res.data)
        self.assertNotIn(serializer_movie_3.data, res.data)

    def test_filter_by_actors(self):
        movie_1 = sample_movie()
        movie_2 = sample_movie(
            title="The Departed",
            description="Sample description",
            duration=100
        )

        actor_1 = sample_actor()
        actor_2 = sample_actor(
            first_name="Leonardo",
            last_name="DiCaprio"
        )
        actor_3 = sample_actor(
            first_name="Bruce",
            last_name="Willis"
        )

        movie_1.actors.add(actor_1)
        movie_2.actors.add(actor_2, actor_3)

        res = self.client.get(MOVIE_URL, {"actors": f"{actor_2.id}, {actor_3.id}"})

        serializer_movie_1 = MovieListSerializer(movie_1)
        serializer_movie_2 = MovieListSerializer(movie_2)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer_movie_2.data, res.data)
        self.assertNotIn(serializer_movie_1.data, res.data)

    def test_filter_by_genres(self):
        movie_1 = sample_movie()
        movie_2 = sample_movie(
            title="The Departed",
            description="Sample description",
            duration=100
        )

        genre_1 = sample_genre()
        genre_2 = sample_genre(
            name="Mystery"
        )
        genre_3 = sample_genre(
            name="Thriller"
        )

        movie_1.genres.add(genre_1)
        movie_2.genres.add(genre_2, genre_3)

        res = self.client.get(MOVIE_URL, {"genres": f"{genre_2.id}, {genre_3.id}"})

        serializer_movie_1 = MovieListSerializer(movie_1)
        serializer_movie_2 = MovieListSerializer(movie_2)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer_movie_2.data, res.data)
        self.assertNotIn(serializer_movie_1.data, res.data)

    def test_retrieve_bus_detail(self):
        movie = sample_movie()
        actor_1 = sample_actor()
        actor_2 = sample_actor(
            first_name="Leonardo",
            last_name="DiCaprio"
        )
        genre_1 = sample_genre()
        genre_2 = sample_genre(
            name="Mystery"
        )
        movie.genres.add(genre_1, genre_2)
        movie.actors.add(actor_1, actor_2)

        url = detail_url(movie.id)
        res = self.client.get(url)
        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(serializer.data, res.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "The Departed",
            "description": "Sample description",
            "duration": 100
        }
        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@mail.com",
            password="password",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)

    def test_create_movie_admin_with_actors_and_genres(self):
        actor_1 = sample_actor()
        actor_2 = sample_actor(first_name="Leonardo", last_name="DiCaprio")
        genre_1 = sample_genre()
        genre_2 = sample_genre(name="Mystery")
        payload = {
            "title": "The Departed",
            "description": "Sample description",
            "duration": 100,
            "actors": [actor_1.id, actor_2.id],
            "genres": [genre_1.id, genre_2.id],
        }

        res = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=res.data["id"])

        actors = Actor.objects.all()
        genres = Genre.objects.all()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED,)

        self.assertEqual(payload["title"], movie.title)
        self.assertEqual(payload["description"], movie.description)
        self.assertEqual(payload["duration"], movie.duration)

        self.assertEqual(
            list(movie.actors.values_list("id", flat=True)),
            payload["actors"]
        )
        self.assertEqual(
            list(movie.genres.values_list("id", flat=True)),
            payload["genres"]
        )

        self.assertEqual(genres.count(), 2)
        self.assertEqual(actors.count(), 2)
