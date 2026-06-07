import os
import tempfile
from PIL import Image

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor
from cinema.serializers import MovieListSerializer

MOVIE_URL = reverse("cinema:movie-list")
MOVIE_SESSION_URL = reverse("cinema:moviesession-list")


def sample_image_file():
    ntf = tempfile.NamedTemporaryFile(suffix=".jpg")
    img = Image.new("RGB", (10, 10))
    img.save(ntf, format="JPEG")
    ntf.seek(0)
    return ntf


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
    return reverse("cinema:movie-upload-image", args=[movie_id])


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


class UnauthenticatedMovieApiTests(APITestCase):
    def test_auth_required(self):
        """Checking that an unauthorized user receives a 401"""
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="user@test.com",
            password="testpassword123"
        )
        refresh = RefreshToken.for_user(self.user)
        auth_header = f"Bearer {str(refresh.access_token)}" # noqa: UnresolvedReferences
        self.client.credentials(HTTP_AUTHORIZATION=auth_header)

    def test_list_movies(self):
        """ТTest of getting a list of movies by a regular user"""
        sample_movie()
        res = self.client.get(MOVIE_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_title(self):
        """Name filtering test (?title=...)"""
        movie1 = sample_movie(title="Inception")
        movie2 = sample_movie(title="Avatar")

        res = self.client.get(MOVIE_URL, {"title": "inception"})

        self.assertIn(MovieListSerializer(movie1).data, res.data)
        self.assertNotIn(MovieListSerializer(movie2).data, res.data)

    def test_filter_movies_by_genres(self):
        """Genre filtering test (?genres=1,2)"""
        genre1 = sample_genre(name="Action")
        genre2 = sample_genre(name="Comedy")

        movie1 = sample_movie(title="Action Movie")
        movie1.genres.add(genre1)
        movie2 = sample_movie(title="Comedy Movie")
        movie2.genres.add(genre2)

        res = self.client.get(MOVIE_URL, {"genres": f"{genre1.id}"})

        self.assertIn(MovieListSerializer(movie1).data, res.data)
        self.assertNotIn(MovieListSerializer(movie2).data, res.data)

    def test_filter_movies_by_actors(self):
        """Actor filtering test (?actors=1,2)"""
        actor1 = sample_actor(first_name="Brad", last_name="Pitt")
        actor2 = sample_actor(first_name="Keanu", last_name="Reeves")

        movie1 = sample_movie(title="Fight Club")
        movie1.actors.add(actor1)
        movie2 = sample_movie(title="Matrix")
        movie2.actors.add(actor2)

        res = self.client.get(MOVIE_URL, {"actors": f"{actor1.id}"})

        self.assertIn(MovieListSerializer(movie1).data, res.data)
        self.assertNotIn(MovieListSerializer(movie2).data, res.data)

    def test_create_movie_forbidden(self):
        """A regular user cannot create movies (403 Forbidden)"""
        payload = {
            "title": "Forbidden Movie",
            "description": "No description",
            "duration": 100
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class MovieImageUploadTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        refresh = RefreshToken.for_user(self.user)
        auth_header = f"Bearer {str(refresh.access_token)}" # noqa: UnresolvedReferences
        self.client.credentials(HTTP_AUTHORIZATION=auth_header)

        self.movie = sample_movie()
        self.genre = sample_genre()
        self.actor = sample_actor()
        self.movie_session = sample_movie_session(movie=self.movie)

    def tearDown(self):
        if self.movie.image:
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
                    "genres": [self.genre.id],
                    "actors": [self.actor.id],
                    "image": ntf,
                },
                format="multipart",
            )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(title="Title")
        self.assertFalse(movie.image)

    def test_image_url_is_shown_on_movie_detail(self):
        url = image_upload_url(self.movie.id)
        with sample_image_file() as ntf:
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(detail_url(self.movie.id))

        self.assertIn("image", res.data)

    def test_image_url_is_shown_on_movie_list(self):
        url = image_upload_url(self.movie.id)
        with sample_image_file() as ntf:
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(MOVIE_URL)

        self.assertIn("image", res.data[0].keys())

    def test_image_url_is_shown_on_movie_session_detail(self):
        url = image_upload_url(self.movie.id)
        with sample_image_file() as ntf:
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(MOVIE_SESSION_URL)

        self.assertIn("movie_image", res.data[0].keys())
