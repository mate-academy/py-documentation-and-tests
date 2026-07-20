from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import Movie

MOVIE_URL = reverse("cinema:movie-list")


def sample_movie(**params):
    defaults = {
        "title": "Sample Movie",
        "description": "Sample Movie Description",
        "duration": 100,
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


class UnauthenticatedMovieApiTest(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_auth_required_for_movies(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com",
            password="testpassword",
        )
        self.client.force_authenticate(user=self.user)

    def test_filter_movies_by_title(self):
        movie_1 = sample_movie(title="Movie 1")
        sample_movie(title="Movie 2")

        res = self.client.get(MOVIE_URL, {"title": "Movie 1"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], movie_1.title)

    def test_retrieve_movie_details(self):
        movie = sample_movie()
        url = detail_url(movie.id)

        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["title"], movie.title)

    def test_create_movie_forbidden(self):
        payload = {"title": "New", "duration": 90}
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_movie_forbidden(self):
        movie = sample_movie()
        url = detail_url(movie.id)
        payload = {"title": "Updated"}

        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_movie_forbidden(self):
        movie = sample_movie()
        url = detail_url(movie.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    class AdminMovieApiTests(TestCase):
        def setUp(self):
            self.client = APIClient()
            self.admin_user = get_user_model().objects.create_superuser(
                email="admin@admin.com",
                password="adminpassword"
            )
            self.client.force_authenticate(self.admin_user)

        def test_create_movie(self):
            payload = {"title": "Admin Movie", "duration": 130}
            res = self.client.post(MOVIE_URL, payload)
            self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        def test_update_movie(self):
            movie = sample_movie()
            url = detail_url(movie.id)
            payload = {"title": "Updated by Admin"}

            res = self.client.patch(url, payload)
            movie.refresh_from_db()

            self.assertEqual(res.status_code, status.HTTP_200_OK)
            self.assertEqual(movie.title, "Updated by Admin")

        def test_delete_movie(self):
            movie = sample_movie()
            url = detail_url(movie.id)

            res = self.client.delete(url)

            self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
            self.assertFalse(Movie.objects.filter(id=movie.id).exists())
