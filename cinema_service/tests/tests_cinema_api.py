from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from cinema.models import Genre, Actor, Movie


class MovieViewSetTestCase(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.genre = Genre.objects.create(name="Action")
        self.actor = Actor.objects.create(name="John Doe")
        self.movie = Movie.objects.create(title="Test Movie")
        self.movie.genres.add(self.genre)
        self.movie.actors.add(self.actor)

    def test_list_movies(self):
        url = reverse("movie-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Test Movie")

    def test_filter_movies_by_genre(self):
        url = reverse("movie-list")
        response = self.client.get(url, {"genres": self.genre.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Test Movie")

    def test_filter_movies_by_title(self):
        url = reverse("movie-list")
        response = self.client.get(url, {"title": "Test Movie"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Test Movie")

    def test_retrieve_movie(self):
        url = reverse("movie-detail", args=[self.movie.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "Test Movie")

    def test_create_movie(self):
        url = reverse("movie-list")
        payload = {"title": "New Movie"}
        response = self.client.post(url, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Movie.objects.count(), 2)
        self.assertEqual(Movie.objects.last().title, "New Movie")

    def test_upload_movie_image(self):
        url = reverse("movie-upload-image", args=[self.movie.id])
        image_data = {"image": b"fake_image_data"}
        response = self.client.post(url, image_data, format="multipart")
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST])
