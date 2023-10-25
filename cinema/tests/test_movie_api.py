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


def detail_url(movie_id: int):
    return reverse("cinema:movie-detail", args=[movie_id])


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
        result = self.client.get(MOVIE_URL)
        self.assertEqual(result.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@user.com",
            password="T1e2S3t4"
        )
        self.client.force_authenticate(self.user)

    def test_list_movies(self):
        drama = sample_genre(name="Drama")
        thriller = sample_genre(name="Thriller")

        forrest_gump = sample_movie(title="Forrest Gump")
        shine = sample_movie(title="Shine")

        forrest_gump.genres.add(drama)
        shine.genres.add(thriller)

        result = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(result.status_code, status.HTTP_200_OK)
        self.assertEqual(result.data, serializer.data)

    def test_movies_filter_by_genres(self):
        drama = sample_genre(name="Drama")
        thriller = sample_genre(name="Thriller")

        forrest_gump = sample_movie(title="Forrest Gump")
        shine = sample_movie(title="Shine")
        movie_without_genres = sample_movie(title="Movie without genres")

        forrest_gump.genres.add(drama)
        shine.genres.add(thriller)

        result = self.client.get(
            MOVIE_URL, {"genres": f"{drama.id}, {thriller.id}"}
        )

        serializer1 = MovieListSerializer(forrest_gump)
        serializer2 = MovieListSerializer(shine)
        serializer3 = MovieListSerializer(movie_without_genres)

        self.assertIn(serializer1.data, result.data)
        self.assertIn(serializer2.data, result.data)
        self.assertNotIn(serializer3.data, result.data)

    def test_movies_filter_by_actors(self):
        brad_pitt = sample_actor(first_name="Brad", last_name="Pitt")
        anthony_hopkins = sample_actor(
            first_name="Anthony", last_name="Hopkins"
        )

        fight_club = sample_movie(title="Fight club")
        the_silence_of_the_lambs = sample_movie(
            title="The Silence Of The Lambs"
        )
        movie_without_actors = sample_movie(title="Movie without actors")

        fight_club.actors.add(brad_pitt)
        the_silence_of_the_lambs.actors.add(anthony_hopkins)

        result = self.client.get(
            MOVIE_URL, {"actors": f"{brad_pitt.id}, {anthony_hopkins.id}"}
        )

        serializer1 = MovieListSerializer(fight_club)
        serializer2 = MovieListSerializer(the_silence_of_the_lambs)
        serializer3 = MovieListSerializer(movie_without_actors)

        self.assertIn(serializer1.data, result.data)
        self.assertIn(serializer2.data, result.data)
        self.assertNotIn(serializer3.data, result.data)

    def test_movies_filter_by_title(self):
        snatch = sample_movie(title="Snatch")
        interstellar = sample_movie(title="Interstellar")

        result = self.client.get(
            MOVIE_URL, {"titles": f"{snatch.id}, {interstellar.id}"}
        )

        serializer1 = MovieListSerializer(snatch)
        serializer2 = MovieListSerializer(interstellar)

        self.assertIn(serializer1.data, result.data)
        self.assertIn(serializer2.data, result.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie(title="movie")
        actor = sample_actor(first_name="actor", last_name="test")
        genre = sample_genre(name="genre")

        movie.actors.add(actor)
        movie.genres.add(genre)

        url = detail_url(movie.id)
        result = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(result.status_code, status.HTTP_200_OK)
        self.assertEqual(result.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "movie",
            "description": "description",
            "duration": 77,
        }

        result = self.client.post(MOVIE_URL, payload)
        self.assertEqual(result.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = get_user_model().objects.create_user(
            email="admintest@user.com",
            password="A1d2M3i4N5",
            is_staff=True
        )
        self.client.force_authenticate(self.admin)

    def test_create_movie(self):
        payload = {
            "title": "movie",
            "description": "description",
            "duration": 77,
        }

        result = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=result.data["id"])

        self.assertEqual(result.status_code, status.HTTP_201_CREATED)

        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_create_movie_with_unnecessary_fields(self):
        actor = sample_actor(first_name="actor", last_name="test")
        genre = sample_genre(name="genre")
        payload = {
            "title": "movie",
            "description": "description",
            "duration": 77,
            "actors": [actor.id],
            "genres": [genre.id],
        }

        result = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=result.data["id"])
        actors = movie.actors.all()
        genres = movie.genres.all()

        self.assertEqual(result.status_code, status.HTTP_201_CREATED)
        self.assertIn(actor, actors)
        self.assertIn(genre, genres)

    def test_delete_movie_not_allowed(self):
        movie = sample_movie()
        url = detail_url(movie.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
