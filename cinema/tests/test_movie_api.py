import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient, APITestCase
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
        if self.movie.image:
            self.movie.image.delete(save=False)

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


class PublicMovieApiTests(APITestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required_for_create(self):
        payload = {
            "title": "Inception",
            "description": "Mind bending thriller",
            "duration": 148,
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateMovieApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="test@cinema.com", password="testpass123"
        )
        self.admin_user = get_user_model().objects.create_superuser(
            email="admin@cinema.com", password="admin123"
        )
        self.client = APIClient()
        self.client.force_authenticate(self.admin_user)

    def test_list_movies(self):
        sample_movie(title="Matrix")
        sample_movie(title="John Wick")

        self.client.force_authenticate(user=self.user)
        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)
        self.assertIn("title", res.data[0])
        self.assertIn("genres", res.data[0])

    def test_create_movie(self):
        genre = sample_genre(name="Thriller")
        actor = sample_actor(first_name="Leonardo", last_name="DiCaprio")

        payload = {
            "title": "Inception",
            "description": "Dream layers",
            "duration": 150,
            "genres": [genre.id],
            "actors": [actor.id],
        }
        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(id=res.data["id"])
        self.assertEqual(movie.title, payload["title"])
        self.assertIn(genre, movie.genres.all())
        self.assertIn(actor, movie.actors.all())

    def test_filter_by_title(self):
        m1 = sample_movie(title="Inception")
        m2 = sample_movie(title="Avatar")

        res = self.client.get(MOVIE_URL, {"title": "inception"})

        self.assertIn(m1.title, [m["title"] for m in res.data])
        self.assertNotIn(m2.title, [m["title"] for m in res.data])

    def test_filter_by_genre(self):
        genre1 = sample_genre(name="Sci-Fi")
        genre2 = sample_genre(name="Drama")
        movie1 = sample_movie(title="Matrix")
        movie1.genres.set([genre1])
        movie2 = sample_movie(title="Titanic")
        movie2.genres.set([genre2])

        res = self.client.get(MOVIE_URL, {"genres": f"{genre1.id}"})

        titles = [m["title"] for m in res.data]
        self.assertIn(movie1.title, titles)
        self.assertNotIn(movie2.title, titles)

    def test_filter_by_actor(self):
        actor1 = sample_actor(first_name="Brad", last_name="Pitt")
        actor2 = sample_actor(first_name="Johnny", last_name="Depp")
        movie1 = sample_movie(title="Fight Club")
        movie1.actors.set([actor1])
        movie2 = sample_movie(title="Pirates")
        movie2.actors.set([actor2])

        res = self.client.get(MOVIE_URL, {"actors": f"{actor1.id}"})

        self.assertIn(movie1.title, [m["title"] for m in res.data])
        self.assertNotIn(movie2.title, [m["title"] for m in res.data])

    def test_retrieve_movie(self):
        movie = sample_movie(title="Interstellar")
        res = self.client.get(detail_url(movie.id))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["title"], "Interstellar")

    def test_update_movie(self):
        movie = sample_movie(title="Old title")
        payload = {
            "title": "New title",
            "description": "Updated",
            "duration": 100,
            "genres": [],
            "actors": [],
        }
        res = self.client.put(detail_url(movie.id), payload)
        movie.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(movie.title, "New title")

    def test_partial_update_movie(self):
        movie = sample_movie(title="Title")
        payload = {"title": "Patched title"}
        res = self.client.patch(detail_url(movie.id), payload)
        movie.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(movie.title, "Patched title")

    def test_delete_movie(self):
        movie = sample_movie(title="To delete")
        res = self.client.delete(detail_url(movie.id))
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Movie.objects.filter(id=movie.id).exists())

    def test_non_admin_cannot_upload_image(self):
        self.client.force_authenticate(self.user)
        movie = sample_movie(title="No upload")
        url = image_upload_url(movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (5, 5))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(url, {"image": ntf}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
