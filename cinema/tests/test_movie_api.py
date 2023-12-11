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
            created_movie_response = self.client.post(
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

        self.assertEqual(created_movie_response.status_code, status.HTTP_201_CREATED)
        movie_with_actor = Movie.objects.get(title="Title")
        self.assertFalse(movie_with_actor.image)

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
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self):
        authentication_response = self.client.get(MOVIE_URL)
        self.assertEqual(authentication_response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@test.com",
            "testpassword",
        )
        self.client.force_authenticate(self.user)

    def test_movies_list_access(self):
        movie1 = sample_movie()
        movie2 = sample_movie()

        movies_list_response = self.client.get(MOVIE_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(movies_list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(movies_list_response.data, serializer.data)

    def test_filter_movies_by_title(self):
        movie_with_title1 = sample_movie(title="Movie1")
        movie_with_title2 = sample_movie(title="Movie2")
        movie_without_title = sample_movie(title="test title")

        filtered_movies_response = self.client.get(MOVIE_URL, {"title": "mov"})

        serializer_with_title1 = MovieListSerializer(movie_with_title1)
        serializer_with_title2 = MovieListSerializer(movie_with_title2)
        serializer_without_title = MovieListSerializer(movie_without_title)

        self.assertIn(serializer_with_title1.data, filtered_movies_response.data)
        self.assertIn(serializer_with_title2.data, filtered_movies_response.data)
        self.assertNotIn(serializer_without_title.data, filtered_movies_response.data)

    def test_filter_movies_by_genres(self):
        movie_with_genre1 = sample_movie(title="movie1")
        movie_with_genre2 = sample_movie(title="movie2")
        movie_without_genre = sample_movie(title="movie without genre")

        genre1 = sample_genre(name="genre1")
        genre2 = sample_genre(name="genre2")

        movie_with_genre1.genres.add(genre1)
        movie_with_genre2.genres.add(genre2)

        filtered_movies_response = self.client.get(MOVIE_URL, {"genres": f"{genre1.id}, {genre2.id}"})

        serializer_with_genre1 = MovieListSerializer(movie_with_genre1)
        serializer_with_genre2 = MovieListSerializer(movie_with_genre2)
        serializer_without_genre = MovieListSerializer(movie_without_genre)

        self.assertIn(serializer_with_genre1.data, filtered_movies_response.data)
        self.assertIn(serializer_with_genre2.data, filtered_movies_response.data)
        self.assertNotIn(serializer_without_genre.data, filtered_movies_response.data)

    def test_filter_movies_by_actors(self):
        movie_with_actor = sample_movie(title="movie")
        movie_with_actor1 = sample_movie(title="movie1")
        movie_without_actor = sample_movie(title="movie2")

        actor1 = sample_actor()
        actor2 = sample_actor(first_name="John")

        movie_with_actor.actors.add(actor1)
        movie_with_actor1.actors.add(actor2)

        filtered_movies_response = self.client.get(MOVIE_URL, {"actors": f"{actor1.id},{actor2.id}"})

        serializer_with_actor = MovieListSerializer(movie_with_actor)
        serializer_with_actor1 = MovieListSerializer(movie_with_actor1)
        serializer_without_actor = MovieListSerializer(movie_without_actor)

        self.assertIn(serializer_with_actor.data, filtered_movies_response.data)
        self.assertIn(serializer_with_actor1.data, filtered_movies_response.data)
        self.assertNotIn(serializer_without_actor.data, filtered_movies_response.data)

    def test_retrieve_movie_detail(self):
        movie_with_genre = sample_movie(title="movie1")
        genre1 = sample_genre(name="genre1")

        movie_with_genre.genres.add(genre1)

        detail_url_response = self.client.get(detail_url(movie_with_genre.id))

        serializer_movie_with_genre = MovieDetailSerializer(movie_with_genre)

        self.assertEqual(detail_url_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_url_response.data, serializer_movie_with_genre.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Sample movie",
            "description": "Sample description",
            "duration": 90,
        }
        create_movie_response = self.client.post(MOVIE_URL, payload)
        self.assertEqual(create_movie_response.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@admin.com",
            "testpassword",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)

    def test_create_movie_with_genre_and_actor(self):
        genre1 = sample_genre(name="genre1")
        genre2 = sample_genre(name="genre2")
        actor1 = sample_actor(first_name="Test", last_name="actor1")
        actor2 = sample_actor(first_name="Test", last_name="actor2")

        payload = {
            "title": "Sample movie",
            "description": "Sample description",
            "duration": 90,
            "genres": [genre1.id, genre2.id],
            "actors": [actor1.id, actor2.id]
        }

        created_movie_response = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=created_movie_response.data["id"])
        genres = movie.genres.all()
        actors = movie.actors.all()

        self.assertEqual(created_movie_response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(genres.count(), 2)
        self.assertIn(genre1, genres)
        self.assertIn(genre2, genres)

        self.assertEqual(actors.count(), 2)
        self.assertIn(actor1, actors)
        self.assertIn(actor2, actors)

    def test_delete_movie_not_allowed(self):
        movie = sample_movie()
        url = detail_url(movie.id)

        deletion_response = self.client.delete(url)

        self.assertEqual(deletion_response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
