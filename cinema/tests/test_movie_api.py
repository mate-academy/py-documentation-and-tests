import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient, APITestCase
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor
from cinema.serializers import (
    MovieSerializer,
    MovieListSerializer,
    MovieDetailSerializer,
)

MOVIE_URL = reverse("cinema:movie-list")
MOVIE_SESSION_URL = reverse("cinema:moviesession-list")

MOVIE_PAYLOAD = {
    "title": "Dune: Part Two",
    "description": (
        "Paul Atreides unites with "
        "Chani and the Fremen while "
        "seeking revenge against "
        "the conspirators who destroyed "
        "his family."
    ),
    "duration": "120",
}


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


class UnauthenticatedMovieTestCase(APITestCase):

    def setUp(self):
        self.client = APIClient()

    def test_authenticate_required(self):
        response = self.client.get(MOVIE_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieTestCase(APITestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin_user = get_user_model().objects.create_superuser(
            email="admin@example.com", password="password123"
        )
        self.user = get_user_model().objects.create_user(
            email="test@mail.com",
            password="Test"
        )
        # self.movie = Movie.objects.create(
        #     title="Dune: Part Two",
        #     description=(
        #         "Paul Atreides unites with "
        #         "Chani and the Fremen while "
        #         "seeking revenge against "
        #         "the conspirators who destroyed "
        #         "his family."
        #     ),
        #     duration="120",
        # )

    def test_authenticated_movie(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(MOVIE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_movies_list(self):
        """Test retrieving a movie list"""
        sample_movie()
        movie_with_genres = sample_movie()

        genre1 = sample_genre(name="Sci-Fi")
        genre2 = sample_genre(name="Western")
        movie_with_genres.genres.add(genre1, genre2)
        movie_with_genres.save()

        self.client.force_authenticate(user=self.user)
        response = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"], serializer.data)

    def test_create_movie_admin_user(self):
        """Test creating a new movie"""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(MOVIE_URL, MOVIE_PAYLOAD)

        self.assertEqual(response.data["title"], MOVIE_PAYLOAD["title"])
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Movie.objects.count(), 1)

    def test_create_movie_authenticated_user(self):
        """Test creating a new movie by an authenticated user"""
        self.client.force_authenticate(user=self.user)

        response = self.client.post(MOVIE_URL, MOVIE_PAYLOAD)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_movie_detail(self):
        """Test retrieving a movie detail"""
        movie = sample_movie()
        url = detail_url(movie.id)

        self.client.force_authenticate(user=self.user)
        response = self.client.get(url)
        serializer = MovieDetailSerializer(movie)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_filter_movie_by_genres(self):
        movie_without_genres = sample_movie()

        genre_sci_fi = sample_genre(name="Sci-Fi")
        genre_adventure = sample_genre(name="Adventure")

        movie_with_genre_sci_fi = sample_movie(title="Dune")
        movie_with_genres_adventure = sample_movie(title="Dune. Part Two")

        movie_with_genre_sci_fi.genres.add(genre_sci_fi)
        movie_with_genres_adventure.genres.add(genre_adventure)

        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            MOVIE_URL,
            {
                "genres": f"{genre_sci_fi.id}, {genre_adventure.id}",
            },
        )
        serializer_movie_without_genres = MovieListSerializer(movie_without_genres)
        serializer_movie_with_genre_sci_fi = MovieListSerializer(
            movie_with_genre_sci_fi
        )
        serializer_movie_with_genre_adventure = MovieListSerializer(
            movie_with_genres_adventure
        )

        self.assertIn(serializer_movie_with_genre_sci_fi.data, response.data["results"])
        self.assertIn(
            serializer_movie_with_genre_adventure.data, response.data["results"]
        )
        self.assertNotIn(serializer_movie_without_genres, response.data["results"])

    def test_filter_movies_by_actors(self):
        movie_without_actors = sample_movie()
        movie_with_actor_dicaprio = sample_movie(title="Titanic")
        movie_with_actress_winslet = sample_movie(
            title="Eternal Sunshine of the Spotless Mind"
        )

        actor_dicaprio = sample_actor(first_name="Leonardo", last_name="DiCaprio")
        actress_winslet = sample_actor(first_name="Kate", last_name="Winslet")
        movie_with_actor_dicaprio.actors.add(actor_dicaprio)
        movie_with_actress_winslet.actors.add(actress_winslet)

        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            MOVIE_URL,
            {
                "actors": f"{actor_dicaprio.id}, {actress_winslet.id}",
            },
        )
        serializer_movie_without_actors = MovieListSerializer(movie_without_actors)
        serializer_movie_with_actor_dicaprio = MovieListSerializer(
            movie_with_actor_dicaprio
        )
        serializer_movie_with_actress_winslet = MovieListSerializer(
            movie_with_actress_winslet
        )

        self.assertIn(
            serializer_movie_with_actor_dicaprio.data, response.data["results"]
        )
        self.assertIn(
            serializer_movie_with_actress_winslet.data, response.data["results"]
        )
        self.assertNotEqual(
            serializer_movie_without_actors.data, response.data["results"]
        )

    def test_filter_movie_by_title(self):
        lord_of_the_rings_movie = sample_movie(
            title="The Lord of the Rings: The Return of the King"
        )
        the_revenant = sample_movie(title="The Revenant")

        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            MOVIE_URL,
            {
                "title": f"{lord_of_the_rings_movie.title}",
            },
        )
        serializer_lord_of_the_rings_movie = MovieListSerializer(
            lord_of_the_rings_movie
        )
        serializer_the_revenant = MovieListSerializer(the_revenant)

        self.assertIn(serializer_lord_of_the_rings_movie.data, response.data["results"])
        self.assertNotIn(serializer_the_revenant.data, response.data["results"])


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

        self.assertIn("image", res.data["results"][0].keys())

    def test_image_url_is_shown_on_movie_session_detail(self):
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(MOVIE_SESSION_URL)

        self.assertIn("movie_image", res.data[0].keys())
