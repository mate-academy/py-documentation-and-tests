import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import (
    Movie,
    MovieSession,
    CinemaHall,
    Genre,
    Actor,
)
from cinema.serializers import (
    MovieDetailSerializer,
    MovieListSerializer,
    MovieSerializer,
)

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


class UnauthenticatedMovieTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_unauthenticated_list_denied(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user("user@test.com", "testpass123")
        self.client.force_authenticate(self.user)

    def test_movie_list(self):
        genre = sample_genre(name="Drama")
        actor = sample_actor(first_name="John", last_name="Doe")
        movie = sample_movie(title="Test Movie")
        movie.genres.add(genre)
        movie.actors.add(actor)

        res = self.client.get(MOVIE_URL)
        movie = Movie.objects.get(id=res.data[0]["id"])
        serializer = MovieListSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data[0], serializer.data)

    def test_movie_detail(self):
        genre = sample_genre(name="Action")
        actor = sample_actor(first_name="Jane", last_name="Smith")
        movie = sample_movie(title="Detail Movie")
        movie.genres.add(genre)
        movie.actors.add(actor)

        res = self.client.get(detail_url(movie.id))
        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_by_genre(self):
        movie_without_comedy = sample_movie(title="Thriller Movie")

        movie_with_comedy_1 = sample_movie(title="Comedy Movie 1")
        movie_with_comedy_2 = sample_movie(title="Comedy Movie 2")

        comedy_genre = sample_genre(name="Comedy")
        thriller_genre = sample_genre(name="Thriller")

        movie_with_comedy_1.genres.add(comedy_genre)
        movie_with_comedy_2.genres.add(comedy_genre)
        movie_without_comedy.genres.add(thriller_genre)

        res = self.client.get(MOVIE_URL, {"genres": f"{comedy_genre.id}"})

        serializer_without_comedy = MovieListSerializer(movie_without_comedy)
        serializer_with_comedy_1 = MovieListSerializer(movie_with_comedy_1)
        serializer_with_comedy_2 = MovieListSerializer(movie_with_comedy_2)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer_with_comedy_1.data, res.data)
        self.assertIn(serializer_with_comedy_2.data, res.data)
        self.assertNotIn(serializer_without_comedy.data, res.data)

    def test_filter_by_title(self):
        movie1 = sample_movie(title="A Test Movie")
        movie2 = sample_movie(title="Another test movie")
        movie3 = sample_movie(title="Different One")

        res = self.client.get(MOVIE_URL, {"title": "test"})
        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie3)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_filter_by_actors(self):
        actor1 = sample_actor(first_name="Actor", last_name="One")
        actor2 = sample_actor(first_name="Actor", last_name="Two")

        movie1 = sample_movie(title="Movie with Actor One")
        movie1.actors.add(actor1)

        movie2 = sample_movie(title="Movie with Actor Two")
        movie2.actors.add(actor2)

        movie3 = sample_movie(title="Movie with Both Actors")
        movie3.actors.add(actor1, actor2)

        res = self.client.get(MOVIE_URL, {"actors": f"{actor1.id},{actor2.id}"})
        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie3)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertIn(serializer3.data, res.data)

    def test_filter_multiple(self):
        actor1 = sample_actor(first_name="Famous", last_name="Actor")
        actor2 = sample_actor(first_name="Another", last_name="Person")

        movie1 = sample_movie(title="Action Movie")
        movie1.actors.add(actor1)

        movie2 = sample_movie(title="Action Comedy")
        movie2.actors.add(actor2)

        movie3 = sample_movie(title="Just a Movie")
        movie3.actors.add(actor1)

        res = self.client.get(MOVIE_URL, {"title": "action", "actors": f"{actor1.id}"})
        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie3)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_non_admin_cannot_create_movie(self):
        payload = {
            "title": "New Movie",
            "description": "Description",
            "duration": 120,
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_non_admin_cannot_update_movie(self):
        movie = sample_movie()
        payload = {"title": "Updated Title"}
        url = detail_url(movie.id)

        # Test PUT
        res_put = self.client.put(url, payload)
        self.assertEqual(res_put.status_code, status.HTTP_403_FORBIDDEN)

        # Test PATCH
        res_patch = self.client.patch(url, payload)
        self.assertEqual(res_patch.status_code, status.HTTP_403_FORBIDDEN)

    def test_non_admin_cannot_delete_movie(self):
        movie = sample_movie()
        url = detail_url(movie.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Movie.objects.filter(id=movie.id).exists())


class AdminMovieTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_user = get_user_model().objects.create_superuser(
            "admin@test.com", "adminpass123"
        )
        self.client.force_authenticate(self.admin_user)
        self.movie = sample_movie()
        self.genre = sample_genre()
        self.actor = sample_actor()

    def test_admin_can_create_movie(self):
        payload = {
            "title": "Admin Movie",
            "description": "Created by admin",
            "duration": 150,
            "genres": [self.genre.id],
            "actors": [self.actor.id],
        }
        res = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=res.data["id"])
        serializer = MovieSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data, serializer.data)

    def test_admin_can_update_movie(self):
        """Test admin can PUT a movie."""
        url = detail_url(self.movie.id)
        new_genre = sample_genre(name="Sci-Fi")
        new_actor = sample_actor(first_name="New", last_name="Actor")
        payload = {
            "title": "Updated Movie",
            "description": "Updated Description",
            "duration": 130,
            "genres": [new_genre.id],
            "actors": [new_actor.id],
        }
        res = self.client.put(url, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.movie.refresh_from_db()
        movie = Movie.objects.get(id=self.movie.id)
        serializer = MovieSerializer(movie)

        self.assertEqual(res.data, serializer.data)
        self.assertIn(new_genre, self.movie.genres.all())
        self.assertIn(new_actor, self.movie.actors.all())

    def test_admin_can_partial_update_movie(self):
        """Test admin can PATCH a movie."""
        url = detail_url(self.movie.id)
        payload = {"title": "Partially Updated"}
        res = self.client.patch(url, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.movie.refresh_from_db()
        self.assertEqual(self.movie.title, payload["title"])

    def test_admin_can_delete_movie(self):
        """Test admin can delete a movie."""
        movie = sample_movie()
        url = detail_url(movie.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Movie.objects.filter(id=movie.id).exists())
