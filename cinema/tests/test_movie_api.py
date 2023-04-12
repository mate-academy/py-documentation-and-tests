import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient, APITestCase
from rest_framework import status
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


class JWTAuthorizationRelatedTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="test_user@example.com", password="password"
        )

        self.token = str(AccessToken.for_user(self.user))

        self.movie = Movie.objects.create(
            title="The Matrix",
            description="A computer hacker learns from mysterious rebels"
                        " about the true nature of his reality and his role "
                        "in the war against its controllers.",
            duration=120,
        )

    def test_list_movies_authenticated(self):
        response = self.client.get(
            MOVIE_URL, HTTP_AUTHORIZATION=f"Bearer {self.token}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_movies_unauthenticated(self):
        response = self.client.get(MOVIE_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_movie_authenticated(self):
        url = reverse("cinema:movie-detail", args=[self.movie.pk])
        response = self.client.get(
            url, HTTP_AUTHORIZATION=f"Bearer {self.token}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_movie_unauthenticated(self):
        url = reverse("cinema:movie-detail", args=[self.movie.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_movie_authenticated(self):
        data = {
            "title": "The Lion King",
            "description": "A young lion returns to reclaim the throne "
                           "that was stolen from him and his father by his"
                           " treacherous uncle.",
            "duration": 120,
        }
        response = self.client.post(
            MOVIE_URL, data, HTTP_AUTHORIZATION=f"Bearer {self.token}"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_movie_unauthenticated(self):
        data = {
            "title": "The Lion King",
            "description": "A young lion returns to reclaim the throne "
                           "that was stolen from him and his father by his "
                           "treacherous uncle.",
            "duration": 120,
        }
        response = self.client.post(MOVIE_URL, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


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


class MovieViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            email="admin@myproject.com",
            password="password",
        )
        self.client.force_authenticate(self.user)

        self.genre1 = Genre.objects.create(name="Action")
        self.genre2 = Genre.objects.create(name="Comedy")

        self.actor1 = Actor.objects.create(
            first_name="Tom", last_name="Cruise"
        )
        self.actor2 = Actor.objects.create(
            first_name="Jim", last_name="Carrey"
        )

        self.movie1 = Movie.objects.create(
            title="Mission: Impossible",
            description="Action movie about Ethan Hunt",
            duration=120,
        )
        self.movie2 = Movie.objects.create(
            title="The Truman Show",
            description="Comedy-drama about Truman Burbank",
            duration=103,
        )

        self.movie1.genres.set([self.genre1])
        self.movie1.actors.set([self.actor1])
        self.movie2.genres.set([self.genre2])
        self.movie2.actors.set([self.actor2])

    def test_list_movies(self):
        """Test retrieving a list of movies"""
        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)

    def test_list_movies_filtered_by_genres(self):
        """Test retrieving a list of movies filtered by genre"""
        url = MOVIE_URL + "?genres=" + str(self.genre1.id)
        res = self.client.get(url)
        print(url)
        print(self.genre1.id)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)

    def test_list_movies_filtered_by_actors(self):
        """Test retrieving a list of movies filtered by actor"""
        url = MOVIE_URL + "?actors=" + str(self.actor2.id)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)

    def test_list_movies_filtered_by_title(self):
        """Test retrieving a list of movies filtered by title"""
        url = MOVIE_URL + "?title=" + "Impossible"
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)

    def test_retrieve_movie(self):
        """Test retrieving a movie"""
        url = detail_url(self.movie1.id)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["title"], self.movie1.title)
        self.assertEqual(res.data["description"], self.movie1.description)
        self.assertEqual(res.data["duration"], self.movie1.duration)
        self.assertEqual(len(res.data["genres"]), 1)
        self.assertEqual(res.data["genres"][0]["name"], self.genre1.name)
        self.assertEqual(len(res.data["actors"]), 1)
        self.assertEqual(
            res.data["actors"][0]["first_name"], self.actor1.first_name
        )

    def test_create_movie(self):
        """Test creating a movie"""
        payload = {
            "title": "The Matrix",
            "description": "Sci-fi action movie about Neo",
            "duration": 136,
            "genres": [self.genre1.id],
            "actors": [self.actor1.id],
        }
        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(id=res.data["id"])
        for key in payload.keys():
            if key != "genres" and key != "actors":
                self.assertEqual(payload[key], getattr(movie, key))
        self.assertEqual(len(res.data["genres"]), 1)
        self.assertEqual(len(res.data["actors"]), 1)

    def test_update_movie(self):
        """Test updating a movie"""
        payload = {
            "title": "Mission: Impossible II",
            "description": "Action movie about Ethan Hunt, part 2",
            "duration": 130,
            "genres": [self.genre1.id, self.genre2.id],
            "actors": [self.actor1.id, self.actor2.id],
        }
        url = detail_url(self.movie1.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_movie(self):
        """Test deleting a movie"""
        url = detail_url(self.movie1.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class MovieThrottlingTestCase(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="testuser@test.com", password="testpass")

    def test_list_endpoint_throttling(self):
        self.client.force_authenticate(user=self.user)

        for i in range(30):
            response = self.client.get(MOVIE_URL)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(MOVIE_URL)
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
