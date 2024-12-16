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


class UnauthenticatedMovieAoiTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_authRequired(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieAoiTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.test", password="testpassword"
        )
        self.client.force_authenticate(self.user)

    def test_movies_list(self):
        sample_movie()

        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.data, serializer.data)

    def test_movies_list_filter_by_genres(self):
        sample_movie()

        genre_drama = sample_genre(name="Drama")
        genre_horror = sample_genre(name="Horror")

        movie_with_genres = sample_movie()
        movie_with_genres.genres.add(genre_drama, genre_horror)

        res = self.client.get(
            MOVIE_URL, {"genres": f"{genre_drama.id},{genre_horror.id}"}
        )
        movies = Movie.objects.filter(
            genres__id__in=[genre_horror.id, genre_drama.id]
        ).distinct()
        serializer = MovieListSerializer(movies, many=True)
        self.assertEqual(res.data, serializer.data)

    def test_movies_list_filter_by_actors(self):
        sample_movie()

        actor_joe = sample_actor(first_name="Joe", last_name="Biden")
        actor_donald = sample_actor(first_name="Donald", last_name="Trump")

        movie_with_actors = sample_movie()
        movie_with_actors.actors.add(actor_joe, actor_donald)

        res = self.client.get(
            MOVIE_URL, {"actors": f"{actor_joe.id},{actor_donald.id}"}
        )
        movies = Movie.objects.filter(
            actors__id__in=[actor_joe.id, actor_donald.id]
        ).distinct()
        serializer = MovieListSerializer(movies, many=True)
        self.assertEqual(res.data, serializer.data)

    def test_movies_list_filter_by_title(self):
        sample_movie()
        sample_movie(title="Alien")

        res = self.client.get(MOVIE_URL, {"title": "Alien"})
        movies = Movie.objects.filter(title__icontains="Alien").distinct()
        serializer = MovieListSerializer(movies, many=True)
        self.assertEqual(res.data, serializer.data)

    def test_movies_retrive(self):
        movie = sample_movie(title="Alien")
        actor_1 = sample_actor(first_name="Sigurni", last_name="Viver")
        actor_2 = sample_actor(first_name="Thomas", last_name="Skerritt")

        genre_1 = sample_genre(name="Sci-Fi")
        genre_2 = sample_genre(name="Horror")

        movie.actors.add(actor_1, actor_2)
        movie.genres.add(genre_1, genre_2)

        res = self.client.get(reverse("cinema:movie-detail", args=(movie.id,)))
        serializer = MovieDetailSerializer(movie)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbiden(self):
        movie = {
            "title": "Sample movie",
            "description": "Sample description",
            "duration": 90,
        }

        res = self.client.post(MOVIE_URL, movie)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = get_user_model().objects.create_superuser(
            email="admin@admin.admin", password="testpassword"
        )
        self.client.force_authenticate(self.admin)

    def test_create_movie(self):
        payload = {
            "title": "Sample movie",
            "description": "Sample description",
            "duration": 90,
        }

        res = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_create_movie_with_genres_and_actors(self):
        actor_1 = sample_actor(first_name="Sigurni", last_name="Viver")
        actor_2 = sample_actor(first_name="Thomas", last_name="Skerritt")

        genre_1 = sample_genre(name="Sci-Fi")
        genre_2 = sample_genre(name="Horror")
        payload = {
            "title": "Sample movie",
            "description": "Sample description",
            "duration": 90,
            "actors": [actor_1.id, actor_2.id],
            "genres": [genre_1.id, genre_2.id],
        }

        res = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(id=res.data["id"])
        actors = movie.actors.all()
        genres = movie.genres.all()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn(actor_1, actors)
        self.assertIn(actor_2, actors)
        self.assertIn(genre_1, genres)
        self.assertIn(genre_2, genres)
        self.assertEqual(genres.count(), 2)
        self.assertEqual(actors.count(), 2)

    def test_delete_movie_not_allowed(self):
        movie = sample_movie()

        res = self.client.delete(
            reverse("cinema:movie-detail", args=(movie.id,))
        )

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
