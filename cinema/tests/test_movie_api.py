import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
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
        self.movie.image.delete()

    def test_upload_image_to_movie(self):
        """Test uploading an image to movie"""
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(url, {"image": ntf}, 
                                   format="multipart")
        self.movie.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)
        self.assertTrue(os.path.exists(self.movie.image.path))

    def test_upload_image_bad_request(self):
        """Test uploading an invalid image"""
        url = image_upload_url(self.movie.id)
        res = self.client.post(url, {"image": "not image"}, 
                               format="multipart")

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
        
        
class MovieFilterTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)

        self.genre1 = Genre.objects.create(name="Action")
        self.genre2 = Genre.objects.create(name="Comedy")
        self.actor1 = Actor.objects.create(first_name="Tom", 
                                           last_name="Cruise")
        self.actor2 = Actor.objects.create(first_name="Will", 
                                           last_name="Smith")

        self.movie1 = Movie.objects.create(title="Mission Impossible", 
                                           description="Action movie", 
                                           duration=120)
        self.movie1.genres.add(self.genre1)
        self.movie1.actors.add(self.actor1)

        self.movie2 = Movie.objects.create(title="Men in Black", 
                                           description="Comedy action", 
                                           duration=100)
        self.movie2.genres.add(self.genre2)
        self.movie2.actors.add(self.actor2)

    def test_filter_movies_by_title(self):
        res = self.client.get(MOVIE_URL, {"title": "Mission"})
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["id"], self.movie1.id)

    def test_filter_movies_by_genres(self):
        res = self.client.get(MOVIE_URL, {"genres": f"{self.genre1.id}"})
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["id"], self.movie1.id)

    def test_filter_movies_by_actors(self):
        res = self.client.get(MOVIE_URL, {"actors": f"{self.actor2.id}"})
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["id"], self.movie2.id)
        
        
class MovieAccessTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user@test.com", password="password"
        )
        self.admin = get_user_model().objects.create_superuser(
            email="admin@test.com", password="password"
        )
        self.movie = sample_movie()

    def test_list_movies_unauthenticated(self):
        self.client.force_authenticate(user=None)
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_create_movie_as_admin(self):
        genre = Genre.objects.create(name="Drama")
        actor = Actor.objects.create(first_name="Tom", last_name="Hanks")
        self.client.force_authenticate(user=self.admin)
        payload = {"title": "New Movie", "description": "Desc",
                   "duration": 100, "genres": [genre.id], "actors": [actor.id]}
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_create_movie_as_normal_user(self):
        genre = Genre.objects.create(name="Drama")
        actor = Actor.objects.create(first_name="Tom", last_name="Hanks")
        self.client.force_authenticate(user=self.user)
        payload = {"title": "New Movie", "description": "Desc",
                   "duration": 100, "genres": [genre.id], "actors": [actor.id]}
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_movie(self):
        genre = Genre.objects.create(name="Action")
        actor = Actor.objects.create(first_name="Will", last_name="Smith")
        self.movie.genres.add(genre)
        self.movie.actors.add(actor)

        self.client.force_authenticate(user=self.user)
        url = reverse("cinema:movie-detail", args=[self.movie.id])
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], self.movie.id)
        self.assertEqual(res.data["title"], self.movie.title)

        self.assertIn("genres", res.data)
        self.assertEqual(res.data["genres"][0]["id"], genre.id)
        self.assertIn("actors", res.data)
        self.assertEqual(res.data["actors"][0]["id"], actor.id)


class MovieSessionFilterTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@test.com", "password"
        )
        self.client.force_authenticate(self.user)

        self.movie = sample_movie()
        self.session1 = sample_movie_session(movie=self.movie, show_time="2022-06-02 14:00:00")
        self.session2 = sample_movie_session(movie=self.movie, show_time="2022-06-03 16:00:00")

    def test_filter_sessions_by_date(self):
        res = self.client.get(MOVIE_SESSION_URL, {"date": "2022-06-02"})
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["id"], self.session1.id)

    def test_filter_sessions_by_movie(self):
        res = self.client.get(MOVIE_SESSION_URL, {"movie": self.movie.id})
        self.assertEqual(len(res.data), 2)
