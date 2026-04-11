import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status
from yaml import serialize

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor
from cinema.serializers import MovieSerializer

from user.models import User

MOVIE_URL = reverse("cinema:movie-list")
MOVIE_SESSION_URL = reverse("cinema:moviesession-list")

def sample_movie_dic(genre_id, actor_id):
    return  {
        "title": "New Movie Test",
        "description": "Movie description",
        "duration": 123,
        "genres": genre_id,
        "actors": actor_id,
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

def sample_user(**params):
    defaults = {
        "email": "test@cinema.com",
        "password": "(TeSt)+Password",
    }
    defaults.update(params)

    return User.objects.create(**defaults)


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

class MovieUnauthenticatedTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.movie = sample_movie()
        self.genre = sample_genre()
        self.actor = sample_actor()


    def test_movie_list(self):
        url = MOVIE_URL
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


    def test_movie_create(self):
        url = MOVIE_URL

        test_movie = sample_movie_dic(
            [self.genre.id],
            [self.actor.id]
        )
        res = self.client.post(url, test_movie)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

class MovieAuthenticatedTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.movie = sample_movie()
        self.genre = sample_genre()
        self.actor = sample_actor()
        self.user = sample_user()

        self.client.force_authenticate(self.user)

        self.movies = []

        for i in range(1, 6):
            movie = sample_movie(
                title=f"Test{i}",
                description=f"Description{i}",
                duration= i * 10 + 15,
            )
            movie.genres.add(self.genre)
            movie.actors.add(self.actor)

            self.movies.append(movie)

    def test_movie_list(self):
        url = MOVIE_URL
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.json()), 6)

    def test_movie_create(self):

        test_movie = sample_movie_dic(
            [self.genre.id],
            [self.actor.id]
        )

        url = MOVIE_URL
        res = self.client.post(url, test_movie)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


    def test_filter_movies_by_genres(self):

        url = MOVIE_URL
        genre = Genre.objects.create(name="thriller")

        self.movies[0].genres.add(genre)

        filter_movies_by_genre = {
            "genres": str(genre.id)
        }

        res = self.client.get(url, filter_movies_by_genre)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.json()), 1)

    def test_filter_movies_by_actors(self):
        url = MOVIE_URL

        actor = Actor.objects.create(first_name="John", last_name="Doe")

        self.movies[0].actors.add(actor)

        filter_movies_by_genre = {
            "actors": str(actor.id)
        }

        res = self.client.get(url, filter_movies_by_genre)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.json()), 1)


    def test_filter_movies_by_title(self):
        url = MOVIE_URL

        title = Movie.objects.create(title="Title", description="Description", duration=90)

        self.movies.append(title)

        filter_movies_by_genre = {
            "title": title.title
        }

        res = self.client.get(url, filter_movies_by_genre)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.json()), 1)

class MovieAdminTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(email="tesr@ada.com", password="dadwaadaad")

        self.client.force_authenticate(self.user)
        self.genre = sample_genre()
        self.actor = sample_actor()


    def test_movie_create(self):

        test_movie = sample_movie_dic(
            [self.genre.id],
            [self.actor.id]
        )

        url = MOVIE_URL
        res = self.client.post(url, test_movie)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
