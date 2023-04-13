import os
import tempfile

from PIL import Image
from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor
from cinema.serializers import MovieDetailSerializer, MovieListSerializer
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

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


class UnauthenticatedMovieSetApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieSetApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "user@project.com", "password"
        )
        self.client.force_authenticate(self.user)

    def test_list_movies_for_auth_user(self):
        movie_with_genre = sample_movie(title="movie_with_genre")
        movie_with_actors = sample_movie(title="movie_with_actors")

        genre = sample_genre()
        movie_with_genre.genres.add(genre)

        actor = sample_actor()
        movie_with_actors.actors.add(actor)

        res = self.client.get(MOVIE_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_genres_id(self):
        serializers = []
        movies = []
        for i in range(4):
            title = f"Movie {str(i)}"
            movie = sample_movie(title=title)
            name = f"Genre {str(i)}"
            genre = sample_genre(name=name)
            movie.genres.add(genre)
            movies.append(movie)
            serializers.append(MovieListSerializer(movie))

        serializer_without_genre = MovieListSerializer(sample_movie())

        id_str = ",".join(list(map(lambda movie: str(movie.id), movies)))

        res = self.client.get(MOVIE_URL, {"genres": id_str})

        for serializer in serializers:
            self.assertIn(serializer.data, res.data)
        self.assertNotIn(serializer_without_genre.data, res.data)

    def test_filter_movies_by_actors_id(self):
        serializers = []
        movies = []
        for i in range(3):
            title = f"Movie {str(i)}"
            movie = sample_movie(title=title)
            name = f"Test {str(i)}"
            actor = sample_actor(first_name=name)
            movie.actors.add(actor)
            movies.append(movie)
            serializers.append(MovieListSerializer(movie))

        serializer_without_actor = MovieListSerializer(sample_movie())

        id_str = ",".join(list(map(lambda movie: str(movie.id), movies)))

        res = self.client.get(MOVIE_URL, {"actors": id_str})

        for serializer in serializers:
            self.assertIn(serializer.data, res.data)
        self.assertNotIn(serializer_without_actor.data, res.data)

    def test_filter_movies_by_title(self):
        serializers = []
        filter_title = "TestTest"
        for i in range(4):
            title = filter_title
            movie = sample_movie(title=title)
            serializers.append(MovieListSerializer(movie))

        serializer_default_title = MovieListSerializer(sample_movie())

        res = self.client.get(MOVIE_URL, {"title": filter_title.upper()})

        self.assertEqual(len(serializers), len(res.data))
        self.assertNotIn(serializer_default_title.data, res.data)

        res = self.client.get(MOVIE_URL, {"title": filter_title[2:-1].lower()})
        self.assertEqual(len(serializers), len(res.data))

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        url = detail_url(movie.id)
        serializer = MovieDetailSerializer(movie)

        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(serializer.data, res.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Movie",
            "description": "Sample description",
            "duration": 100,
        }
        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@project.com",
            "password",
            is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        payload = {
            "title": "Movie",
            "description": "Sample description",
            "duration": 100,
        }
        res = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_create_movie_with_genres_and_actors(self):
        actor = sample_actor()
        genre = sample_genre()

        payload = {
            "title": "Movie",
            "description": "Sample description",
            "duration": 100,
            "actors": {actor.id},
            "genres": {genre.id}
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

        url = detail_url(movie.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


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
