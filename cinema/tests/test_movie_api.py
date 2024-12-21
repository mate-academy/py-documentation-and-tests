import os
import tempfile

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import AccessToken

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


class MovieSessionViewSetTestCase(APITestCase):

    def setUp(self):
        # Створення користувача
        self.user = get_user_model().objects.create_user(
            email="testuser@example.com",
            password="password123"
        )
        # Генерація JWT-токена
        self.token = str(AccessToken.for_user(self.user))

    def get_auth_headers(self):
        """Метод для отримання заголовків авторизації."""
        return {"Authorization": f"Bearer {self.token}"}

    def test_filter_by_date(self):
        """Test filtering movie sessions by date"""
        response = self.client.get(
            "/api/cinema/movie_sessions/",
            {"date": "2024-12-25"},
            HTTP_AUTHORIZATION=self.get_auth_headers()["Authorization"]
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for session in response.data:
            session_date = session["show_time"].split("T")[0]
            self.assertEqual(session_date, "2024-12-25")

    def test_filter_by_movie(self):
        """Test filtering movie sessions by movie ID"""
        response = self.client.get(
            "/api/cinema/movie_sessions/",
            {"movie": 1},
            HTTP_AUTHORIZATION=self.get_auth_headers()["Authorization"]
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for session in response.data:
            self.assertEqual(session["movie"], 1)

    def test_filter_by_date_and_movie(self):
        """Test filtering movie sessions by both date and movie ID"""
        response = self.client.get(
            "/api/cinema/movie_sessions/",
            {"date": "2024-12-25", "movie": 1},
            HTTP_AUTHORIZATION=self.get_auth_headers()["Authorization"]
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for session in response.data:
            session_date = session["show_time"].split("T")[0]
            self.assertEqual(session_date, "2024-12-25")
            self.assertEqual(session["movie"], 1)

    def test_no_filters(self):
        """Test the movie session list without any filters"""
        response = self.client.get(
            "/api/cinema/movie_sessions/",
            HTTP_AUTHORIZATION=self.get_auth_headers()["Authorization"]
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class MovieViewSetTestCase(APITestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(email="testuser", password="password123")

        response = self.client.post(
            "/api/user/token/",
            {"email": "testuser", "password": "password123"},
        )
        self.access_token = response.data["access"]

    def get_auth_headers(self):
        """Helper method to get the authorization headers."""
        return {"HTTP_AUTHORIZATION": f"Bearer {self.access_token}"}

    def test_filter_by_title(self):
        """Test filtering movies by title"""
        response = self.client.get(
            "/api/cinema/movies/",
            {"title": "Inception"},
            **self.get_auth_headers(),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for movie in response.data:
            self.assertIn("Inception", movie["title"])

    def test_filter_by_genres(self):
        """Test filtering movies by genres"""
        response = self.client.get(
            "/api/cinema/movies/",
            {"genres": "1,2"},
            **self.get_auth_headers(),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for movie in response.data:
            genre_ids = [genre["id"] for genre in movie["genres"]]
            self.assertTrue(all(genre_id in genre_ids for genre_id in [1, 2]))

    def test_filter_by_actors(self):
        """Test filtering movies by actors"""
        response = self.client.get(
            "/api/cinema/movies/",
            {"actors": "1,2"},
            **self.get_auth_headers(),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for movie in response.data:
            actor_ids = [actor["id"] for actor in movie["actors"]]
            self.assertTrue(all(actor_id in actor_ids for actor_id in [1, 2]))

    def test_filter_by_multiple_parameters(self):
        """Test filtering movies by title, genres, and actors"""
        response = self.client.get(
            "/api/cinema/movies/",
            {"title": "Inception", "genres": "1,2", "actors": "1,2"},
            **self.get_auth_headers(),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for movie in response.data:
            self.assertIn("Inception", movie["title"])
            genre_ids = [genre["id"] for genre in movie["genres"]]
            self.assertTrue(all(genre_id in genre_ids for genre_id in [1, 2]))
            actor_ids = [actor["id"] for actor in movie["actors"]]
            self.assertTrue(all(actor_id in actor_ids for actor_id in [1, 2]))

    def test_no_filters(self):
        """Test the movie list without any filters"""
        response = self.client.get(
            "/api/cinema/movies/",
            **self.get_auth_headers(),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class APISchemaTestCase(APITestCase):

    def setUp(self):
        # Створення користувача
        self.user = get_user_model().objects.create_user(email="testuser@example.com", password="password123")
        # Генерація токена для користувача
        self.token = str(AccessToken.for_user(self.user))

    def get_auth_headers(self):
        """Helper method to get the authorization headers."""
        return {"Authorization": f"Bearer {self.token}"}

    def test_movie_session_schema(self):
        """Test if the movie session schema includes the date and movie parameters"""
        response = self.client.get("/api/doc/", HTTP_AUTHORIZATION=self.get_auth_headers()["Authorization"])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("date", str(response.content))
        self.assertIn("movie", str(response.content))

    def test_movie_schema(self):
        """Test if the movie schema includes the title, genres, and actors parameters"""
        response = self.client.get("/api/doc/", HTTP_AUTHORIZATION=self.get_auth_headers()["Authorization"])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("title", str(response.content))
        self.assertIn("genres", str(response.content))
        self.assertIn("actors", str(response.content))