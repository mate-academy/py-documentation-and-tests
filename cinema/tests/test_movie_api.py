import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
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
            email="test@test.com",
            password="testpass123",
        )
        self.client.force_authenticate(self.user)

    def test_movie_list(self):
        sample_movie()
        sample_movie(title="Another movie")

        res = self.client.get(MOVIE_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_movie_detail(self):
        movie = sample_movie()

        url = detail_url(movie.id)
        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden_for_non_admin(self):
        payload = {
            "title": "New movie",
            "description": "Desc",
            "duration": 100,
            "genres": [],
            "actors": [],
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Movie.objects.filter(title="New movie").exists())

    def test_upload_image_forbidden_for_non_admin(self):
        movie = sample_movie()
        url = image_upload_url(movie.id)

        image = SimpleUploadedFile(
            "test.jpg",
            b"file_content",
            content_type="image/jpeg",
        )

        res = self.client.post(url, {"image": image}, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)



class AdminMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_user = get_user_model().objects.create(
            email="admin@test.com",
            password="adminpass123",
            is_staff=True,
        )
        self.client.force_authenticate(self.admin_user)

    def test_create_movie_with_genres_and_actors(self):
        genre1 = sample_genre(name="Action")
        genre2 = sample_genre(name="Drama")
        actor1 = sample_actor(first_name="Tom", last_name="Hanks")
        actor2 = sample_actor(first_name="Natalie", last_name="Portman")

        payload = {
            "title": "Created movie",
            "description": "Some description",
            "duration": 130,
            "genres": [genre1.id, genre2.id],
            "actors": [actor1.id, actor2.id],
        }

        res = self.client.post(MOVIE_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(id=res.data["id"])

        self.assertEqual(movie.title, payload["title"])
        self.assertEqual(movie.duration, payload["duration"])
        self.assertEqual(
            set(movie.genres.values_list("id", flat=True)),
            set(payload["genres"]),
        )
        self.assertEqual(
            set(movie.actors.values_list("id", flat=True)),
            set(payload["actors"]),
        )

    def test_partial_update_not_allowed(self):
        movie = sample_movie()
        url = detail_url(movie.id)

        payload = {"title": "Updated title"}
        res = self.client.patch(url, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        movie.refresh_from_db()
        self.assertNotEqual(movie.title, payload["title"])

    def test_delete_not_allowed(self):
        movie = sample_movie()
        url = detail_url(movie.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertTrue(Movie.objects.filter(id=movie.id).exists())


class MovieFilterTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user@test.com",
            password="testpass123",
        )
        self.client.force_authenticate(self.user)

    def test_filter_movies_by_title(self):
        movie1 = sample_movie(title="The Matrix")
        movie2 = sample_movie(title="Matrix Reloaded")
        movie3 = sample_movie(title="Inception")

        res = self.client.get(MOVIE_URL, {"title": "matrix"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        returned_titles = {movie["title"] for movie in res.data}

        self.assertIn(movie1.title, returned_titles)
        self.assertIn(movie2.title, returned_titles)
        self.assertNotIn(movie3.title, returned_titles)

    def test_filter_movies_by_genres(self):
        genre_action = sample_genre(name="Action")
        genre_drama = sample_genre(name="Drama")

        movie1 = sample_movie(title="Action movie")
        movie1.genres.add(genre_action)

        movie2 = sample_movie(title="Drama movie")
        movie2.genres.add(genre_drama)

        movie3 = sample_movie(title="Mixed movie")
        movie3.genres.add(genre_action, genre_drama)

        res = self.client.get(MOVIE_URL, {"genres": str(genre_action.id)})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        returned_titles = {movie["title"] for movie in res.data}

        self.assertIn(movie1.title, returned_titles)
        self.assertIn(movie3.title, returned_titles)
        self.assertNotIn(movie2.title, returned_titles)

        res = self.client.get(
            MOVIE_URL,
            {"genres": f"{genre_action.id},{genre_drama.id}"}
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        returned_titles = {movie["title"] for movie in res.data}

        self.assertIn(movie1.title, returned_titles)
        self.assertIn(movie2.title, returned_titles)
        self.assertIn(movie3.title, returned_titles)

    def test_filter_movies_by_actors(self):
        actor1 = sample_actor(first_name="Keanu", last_name="Reeves")
        actor2 = sample_actor(first_name="Leonardo", last_name="DiCaprio")

        movie1 = sample_movie(title="Movie with Keanu")
        movie1.actors.add(actor1)

        movie2 = sample_movie(title="Movie with Leo")
        movie2.actors.add(actor2)

        movie3 = sample_movie(title="Movie with both")
        movie3.actors.add(actor1, actor2)

        res = self.client.get(MOVIE_URL, {"actors": str(actor1.id)})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        returned_titles = {movie["title"] for movie in res.data}

        self.assertIn(movie1.title, returned_titles)
        self.assertIn(movie3.title, returned_titles)
        self.assertNotIn(movie2.title, returned_titles)

        res = self.client.get(
            MOVIE_URL,
            {"actors": f"{actor1.id},{actor2.id}"}
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        returned_titles = {movie["title"] for movie in res.data}

        self.assertIn(movie1.title, returned_titles)
        self.assertIn(movie2.title, returned_titles)
        self.assertIn(movie3.title, returned_titles)


