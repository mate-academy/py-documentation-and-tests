import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor
from cinema.serializers import MovieListSerializer

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


class UnauthenticatedMovieApiTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        sample_movie()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)


# class ThrottlingTests(TestCase):
#     def setUp(self):
#         self.client = APIClient()
#         self.user = get_user_model().objects.create_user(
#             email="test@test.test",
#             password="testpassword"
#         )
#         sample_movie()
#
#     def test_auth_throttling(self):
#         url = MOVIE_URL
#         self.client.force_authenticate(user=self.user)
#
#         allowed_requests = 30
#
#         for i in range(allowed_requests):
#             res = self.client.get(url)
#             self.assertEqual(
#                 res.status_code,
#                 status.HTTP_200_OK,
#                 f"Request {i + 1} should have been successful but failed."
#             )
#
#         res = self.client.get(url)
#         self.assertEqual(
#             res.status_code,
#             status.HTTP_429_TOO_MANY_REQUESTS,
#             "The request after the limit should have been throttled (429)."
#         )


class JWTAuthenticationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.test",
            password="password"
        )
        self.token_url = "/api/user/token/"
        sample_movie()

    def test_token_obtain_success(self):
        payload = {
            "email": "test@test.test",
            "password": "password"
        }
        res = self.client.post(self.token_url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("access", res.data)
        self.assertIn("refresh", res.data)

    def test_auth_with_jwt(self):
        payload = {
            "email": "test@test.test",
            "password": "password"
        }
        res = self.client.post(self.token_url, payload)
        access_token = res.data["access"]

        auth_client = APIClient()
        auth_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

        res_auth = auth_client.get(MOVIE_URL)

        self.assertEqual(res_auth.status_code, status.HTTP_200_OK)


class AuthenticatedMovieApiTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.test",
            password="testpassword"
        )
        self.client.force_authenticate(self.user)

    def test_filter_movie_by_title(self):
        movie1 = sample_movie(title="The Terminator")
        sample_movie(title="Avatar")

        res = self.client.get(MOVIE_URL, {"title": "Termin"})

        serializer = MovieListSerializer(movie1)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], serializer.data["title"])

    def test_filter_movie_by_genres(self):
        genre_action = sample_genre(name="Action")
        genre_comedy = sample_genre(name="Comedy")

        movie1 = sample_movie(title="Action Film")
        movie2 = sample_movie(title="Comedy Film")

        movie1.genres.add(genre_action)
        movie2.genres.add(genre_comedy)

        res = self.client.get(MOVIE_URL, {"genres": f"{genre_action.id},{genre_comedy.id}"})
        self.assertEqual(len(res.data), 2)

    def test_movie_list(self):
        sample_movie()
        movie_with_genre = sample_movie()
        movie_with_actors = sample_movie()

        genre_1 = Genre.objects.create(name="Drama")
        actor_1 = Actor.objects.create(first_name="George", last_name="Clooney")

        movie_with_genre.genres.add(genre_1)
        movie_with_actors.actors.add(actor_1)

        res = self.client.get(MOVIE_URL)

        movies = Movie.objects.all().order_by("id")
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Harry Potter",
            "description": "Harry Potter description",
            "duration": 170,
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@test.test",
            password="testpassword",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        genre = Genre.objects.create(name="Action")
        actor = Actor.objects.create(first_name="Will", last_name="Smith")

        payload = {
            "title": "Harry Potter",
            "description": "Harry Potter description",
            "duration": 170,
            "actors": [actor.id],
            "genres": [genre.id]
        }

        res = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        for key in ["title", "description", "duration"]:
            self.assertEqual(payload[key], getattr(movie, key))

        self.assertIn(genre, movie.genres.all())
        self.assertIn(actor, movie.actors.all())

    def test_create_movie_with_actors(self):
        actors_1 = Actor.objects.create(first_name="George", last_name="Clooney")
        genre_for_test = Genre.objects.create(name="Thriller")

        payload = {
            "title": "Harry Potter",
            "description": "Harry Potter description",
            "duration": 170,
            "actors": [actors_1.id],
            "genres": [genre_for_test.id],

        }

        res = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(id=res.data["id"])

        actors = movie.actors.all()
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn(actors_1, actors)
        self.assertEqual(actors.count(), 1)

    def test_create_movie_with_genres(self):
        genres_1 = Genre.objects.create(name="Drama")
        actor_for_test = Actor.objects.create(first_name="Test", last_name="Actor")

        payload = {
            "title": "Harry Potter",
            "description": "Harry Potter description",
            "duration": 170,
            "genres": [genres_1.id],
            "actors": [actor_for_test.id],

        }

        res = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(id=res.data["id"])

        genres = movie.genres.all()
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn(genres_1, genres)
        self.assertEqual(genres.count(), 1)

    def test_delete_movie_not_allowed(self):
        movie = sample_movie()

        url = detail_url(movie.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
