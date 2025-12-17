import tempfile

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor

MOVIE_URL = reverse("cinema:movie-list")


def sample_movie(genres=None, actors=None, **params):
    defaults = {
        "title": "Sample movie",
        "description": "Sample description",
        "duration": 90,
    }
    defaults.update(params)

    movie = Movie.objects.create(**defaults)

    if genres:
        movie.genres.set(genres)
    if actors:
        movie.actors.set(actors)

    return movie


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




def image_upload_url(movie_id):
    """Return URL for movie image upload"""
    return reverse("cinema:movie-upload-image", args=[movie_id])


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


class MovieImageUploadTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = get_user_model().objects.create_superuser(
            email="admin@myproject.com",
            password="password",
        )
        self.client.force_authenticate(self.admin)

        self.genre = sample_genre(name="Sci-Fi")
        self.actor = sample_actor(first_name="Keanu", last_name="Reeves")
        self.movie = sample_movie(genres=[self.genre], actors=[self.actor])

    def tearDown(self):
        if self.movie.image:
            self.movie.image.delete()

    def test_upload_image_to_movie(self):
        url = image_upload_url(self.movie.id)

        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)

            res = self.client.post(url, {"image": ntf}, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.movie.refresh_from_db()
        self.assertTrue(self.movie.image)

    def test_upload_image_bad_request(self):
        url = image_upload_url(self.movie.id)
        res = self.client.post(url, {"image": "notimage"}, format="multipart")

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
                    "genres": [self.genre.id],
                    "actors": [self.actor.id],
                    "image": ntf,
                },
                format="multipart",
            )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(title="Title")
        self.assertFalse(movie.image)


class PublicMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user_public@myproject.com",
            password="password",
        )
        self.client.force_authenticate(self.user)
        self.genre1 = sample_genre(name="Action")
        self.genre2 = sample_genre(name="Drama")
        self.actor1 = sample_actor(first_name="Tom", last_name="Hardy")
        self.actor2 = sample_actor(first_name="Amy", last_name="Adams")

        self.movie1 = sample_movie(
            title="Alpha",
            genres=[self.genre1],
            actors=[self.actor1],
        )
        self.movie2 = sample_movie(
            title="Beta",
            genres=[self.genre2],
            actors=[self.actor2],
        )

    def _unwrap_list(self, data):
        # Supports both paginated and non-paginated responses
        if isinstance(data, dict) and "results" in data:
            return data["results"]
        return data

    def test_list_movies_unauthorized(self):
        self.client.force_authenticate(user=None)
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_movie_detail_unauthorized(self):
        self.client.force_authenticate(user=None)
        res = self.client.get(detail_url(self.movie1.id))
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_movies(self):
        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        items = self._unwrap_list(res.data)
        titles = [m["title"] for m in items]
        self.assertIn("Alpha", titles)
        self.assertIn("Beta", titles)

    def test_retrieve_movie_detail(self):
        res = self.client.get(detail_url(self.movie1.id))

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["title"], "Alpha")

    def test_filter_movies_by_title(self):
        res = self.client.get(MOVIE_URL, {"title": "alp"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        items = self._unwrap_list(res.data)
        titles = [m["title"] for m in items]
        self.assertIn("Alpha", titles)
        self.assertNotIn("Beta", titles)

    def test_filter_movies_by_genres(self):
        res = self.client.get(MOVIE_URL, {"genres": str(self.genre1.id)})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        items = self._unwrap_list(res.data)
        titles = [m["title"] for m in items]
        self.assertIn("Alpha", titles)
        self.assertNotIn("Beta", titles)

    def test_filter_movies_by_actors(self):
        res = self.client.get(MOVIE_URL, {"actors": str(self.actor2.id)})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        items = self._unwrap_list(res.data)
        titles = [m["title"] for m in items]
        self.assertIn("Beta", titles)
        self.assertNotIn("Alpha", titles)


class AdminMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = get_user_model().objects.create_superuser(
            email="admin@myproject.com",
            password="password",
        )
        self.user = get_user_model().objects.create_user(
            email="user@myproject.com",
            password="password",
        )
        self.genre = sample_genre(name="Sci-Fi")
        self.actor = sample_actor(first_name="Keanu", last_name="Reeves")

    def test_create_movie_forbidden_for_regular_user(self):
        self.client.force_authenticate(self.user)
        payload = {
            "title": "New",
            "description": "Desc",
            "duration": 100,
            "genres": [self.genre.id],
            "actors": [self.actor.id],
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_movie_admin_success(self):
        self.client.force_authenticate(self.admin)
        payload = {
            "title": "New",
            "description": "Desc",
            "duration": 100,
            "genres": [self.genre.id],
            "actors": [self.actor.id],
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(title="New")
        self.assertEqual(movie.title, "New")

    def test_update_movie_not_allowed(self):
        self.client.force_authenticate(self.admin)
        movie = sample_movie(title="Original", genres=[self.genre], actors=[self.actor])

        payload = {
            "title": "Updated",
            "description": movie.description,
            "duration": movie.duration,
            "genres": [self.genre.id],
            "actors": [self.actor.id],
        }

        res = self.client.put(detail_url(movie.id), payload)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        movie.refresh_from_db()
        self.assertEqual(movie.title, "Original")

    def test_delete_movie_not_allowed(self):
        self.client.force_authenticate(self.admin)
        movie = sample_movie()

        res = self.client.delete(detail_url(movie.id))

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertTrue(Movie.objects.filter(id=movie.id).exists())


class MovieImageUploadPermissionsTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user@myproject.com",
            password="password",
        )
        self.client.force_authenticate(self.user)
        self.movie = sample_movie()

    def tearDown(self):
        if getattr(self.movie, "image", None):
            self.movie.image.delete()

    def test_upload_image_forbidden_for_regular_user(self):
        url = image_upload_url(self.movie.id)

        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)

            res = self.client.post(url, {"image": ntf}, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
