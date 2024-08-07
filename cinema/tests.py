from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from cinema.models import Movie
from django.contrib.auth import get_user_model

MOVIE_URL = reverse("cinema:movie-list")


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


class MovieApiTests(APITestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@example.com",
            "password123"
        )
        self.client.force_authenticate(self.user)
        self.movie = Movie.objects.create(
            title="Test Movie",
            description="Test Description",
            duration=120
        )

    def test_list_movies(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("title", res.data[0])
        self.assertIn("description", res.data[0])
        self.assertIn("duration", res.data[0])

    def test_movie_detail(self):
        url = detail_url(self.movie.id)
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("title", res.data)
        self.assertIn("description", res.data)
        self.assertIn("duration", res.data)

    def test_create_movie(self):
        payload = {
            "title": "New Movie",
            "description": "New Description",
            "duration": 100
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(id=res.data["id"])
        self.assertEqual(movie.title, payload["title"])
        self.assertEqual(movie.description, payload["description"])
        self.assertEqual(movie.duration, payload["duration"])

    def test_update_movie(self):
        payload = {
            "title": "Updated Movie",
            "description": "Updated Description",
            "duration": 150
        }
        url = detail_url(self.movie.id)
        res = self.client.put(url, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.movie.refresh_from_db()
        self.assertEqual(self.movie.title, payload["title"])
        self.assertEqual(self.movie.description, payload["description"])
        self.assertEqual(self.movie.duration, payload["duration"])

    def test_delete_movie(self):
        url = detail_url(self.movie.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Movie.objects.filter(id=self.movie.id).exists())
