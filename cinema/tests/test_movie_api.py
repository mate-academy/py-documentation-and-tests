import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.core.cache import cache
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


class UnauthenticatedMovieApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_list_movie_unauthorized(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_movie_unauthorized(self):
        movie = sample_movie()
        res = self.client.get(detail_url(movie.id))
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_movie_unauthorized(self):
        payload = {
            "title": "Test Movie",
            "description": "Test description",
            "duration": 90,
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class InvalidTokenAuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@user.test", password="usertestpassword"
        )
        res = self.client.post(
            reverse("token_obtain_pair"),
            {"email": "test@user.test", "password": "usertestpassword"})
        token = res.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token + 'a'}")

    def test_returns_401_with_invalid_token(self):
        response = self.client.get(MOVIE_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("detail", response.data)


class MovieSessionQueryParamsValidationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test1@test1.test", password="1testpassword"
        )
        res = self.client.post(
            reverse("token_obtain_pair"),
            {"email": "test1@test1.test", "password": "1testpassword"})
        token = res.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.assertIn("access", res.data)

    def test_invalid_date_params_return_400(self):
        res = self.client.get(MOVIE_SESSION_URL, {"date": "abc"})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid date format. Use YYYY-MM-DD", str(res.data["detail"]))

    def test_invalid_movie_params_return_400(self):
        res = self.client.get(MOVIE_SESSION_URL, {"movie": "abc"})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid movie ID. Must be integer", str(res.data["detail"]))


class AuthenticatedNotAdminMovieApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test2@test2.test", password="2testpassword"
        )
        res = self.client.post(
            reverse("token_obtain_pair"),
            {"email": "test2@test2.test", "password": "2testpassword"})
        token = res.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.assertIn("access", res.data)

    def test_movies_list_and_retrieve_allowed(self):
        movie = sample_movie()
        res_list = self.client.get(MOVIE_URL)
        res_detail = self.client.get(detail_url(movie.id))
        self.assertEqual(res_list.status_code, status.HTTP_200_OK)
        self.assertEqual(res_detail.status_code, status.HTTP_200_OK)

    def test_create_forbidden(self):
        payload = {
            "title": "Test Movie",
            "description": "Test description",
            "duration": 90,
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_filter_movies_by_genres(self):
        movie_without_genre = sample_movie()
        movie_with_genre = sample_movie()
        genre = sample_genre()
        movie_with_genre.genres.add(genre)

        res = self.client.get(
            MOVIE_URL,
            {
                "genres": f"{genre.id}",
            },
        )
        movies = Movie.objects.filter(genres__id__in=[genre.id])
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Порівнюємо всю відповідь з серіалізованими даними
        self.assertEqual(res.data, serializer.data)
        # Перевіряємо, що фільми із жанрами присутні
        self.assertIn(MovieListSerializer(movie_with_genre).data, res.data)
        # Перевіряємо, що фільми без жанрів відсутні
        self.assertNotIn(MovieListSerializer(movie_without_genre).data, res.data)

    def test_filter_movies_by_actors(self):
        movie_without_actor = sample_movie()
        movie_with_actor = sample_movie()
        actor = sample_actor()
        movie_with_actor.actors.add(actor)

        res = self.client.get(
            MOVIE_URL,
            {"actors": f"{actor.id}"},
        )
        movies = Movie.objects.filter(actors__id__in=[actor.id])
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Порівнюємо всю відповідь з серіалізованими даними
        self.assertEqual(res.data, serializer.data)
        # Перевіряємо, що фільми із акторами присутні
        self.assertIn(MovieListSerializer(movie_with_actor).data, res.data)
        # Перевіряємо, що фільми без акторів відсутні
        self.assertNotIn(MovieListSerializer(movie_without_actor).data, res.data)

    def test_filter_movies_by_title(self):
        movie_match = sample_movie()
        movie_no_match = sample_movie(title="Another Movie")

        res = self.client.get(MOVIE_URL, {"title": movie_match.title})
        movies = Movie.objects.filter(title__icontains=movie_match.title)
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)
        self.assertIn(MovieListSerializer(movie_match).data, res.data)
        self.assertNotIn(MovieListSerializer(movie_no_match).data, res.data)

    def test_filter_movies_by_genres_and_actors(self):
        genre = sample_genre(name="Action")
        actor = sample_actor(first_name="John", last_name="Smith")
        movie_match = sample_movie(title="Match")
        movie_match.genres.add(genre)
        movie_match.actors.add(actor)

        movie_only_genre = sample_movie(title="Only Genre")
        movie_only_genre.genres.add(genre)

        movie_only_actor = sample_movie(title="Only Actor")
        movie_only_actor.actors.add(actor)

        movie_none = sample_movie(title="None")

        res = self.client.get(
            MOVIE_URL,
            {"genres": f"{genre.id}", "actors": f"{actor.id}"},
        )
        movies = Movie.objects.filter(
            genres__id__in=[genre.id], actors__id__in=[actor.id]
        )
        serializers = MovieListSerializer(movies, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializers.data)
        self.assertIn(MovieListSerializer(movie_match).data, res.data)
        self.assertNotIn(MovieListSerializer(movie_only_genre).data, res.data)
        self.assertNotIn(MovieListSerializer(movie_only_actor).data, res.data)
        self.assertNotIn(MovieListSerializer(movie_none).data, res.data)


class AdminMovieApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin = get_user_model().objects.create_superuser(
            email="admin@testadmin.com",
            password="adminpassword",
            is_staff=True,
        )
        res = self.client.post(
            reverse("token_obtain_pair"),
            {"email": "admin@testadmin.com", "password": "adminpassword"})
        token = res.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_create_movie(self):
        genre = sample_genre()
        actor = sample_actor()
        payload = {
            "title": "Test Movie",
            "description": "Test description",
            "duration": 90,
            "genres": [genre.id],
            "actors": [actor.id],
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(id=res.data["id"])
        self.assertIn(genre, movie.genres.all())
        self.assertIn(actor, movie.actors.all())

    def test_movies_list_and_retrieve_allowed(self):
        movie = sample_movie()
        res_list = self.client.get(MOVIE_URL)
        res_detail = self.client.get(detail_url(movie.id))
        self.assertEqual(res_list.status_code, status.HTTP_200_OK)
        self.assertEqual(res_detail.status_code, status.HTTP_200_OK)


class MovieUpdateDeleteNotAllowedTests(TestCase):
    def tearDown(self):
        cache.clear()

    def setUp(self):
        self.client = APIClient()
        self.movie = sample_movie()

    def auth_as_user(self):
        email = "test3@test.test"
        password = "3testpassword"
        get_user_model().objects.create_user(email=email, password=password)
        res = self.client.post(
            reverse("token_obtain_pair"),
            {"email": email, "password": password}
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.assertIn("access", res.data)
        token = res.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def auth_as_admin(self):
        email = "admin@admin.com"
        password = "adminpas"
        get_user_model().objects.create_superuser(email=email, password=password)
        res = self.client.post(
            reverse("token_obtain_pair"),
            {"email": email, "password": password}
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.assertIn("access", res.data)
        token = res.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_put_patch_delete_not_allowed_for_user(self):
        self.auth_as_user()
        url = detail_url(self.movie.id)
        self.assertEqual(self.client.put(url, {"title": "Test Movie"}).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.patch(url, {"title": "Test Movie"}).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.delete(url).status_code, status.HTTP_403_FORBIDDEN)

    def test_put_patch_delete_not_allowed_for_admin(self):
        self.auth_as_admin()
        url = detail_url(self.movie.id)
        self.assertEqual(self.client.put(url, {"title": "Test Movie"}).status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(self.client.patch(url, {"title": "Test Movie"}).status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(self.client.delete(url).status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class MovieImageUploadTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        email = "admin@admin.admin"
        password = "adminpa"
        get_user_model().objects.create_superuser(email=email, password=password)
        res = self.client.post(
            reverse("token_obtain_pair"),
            {"email": email, "password": password}
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.assertIn("access", res.data)
        token = res.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
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
