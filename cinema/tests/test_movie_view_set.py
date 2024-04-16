from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from cinema.models import Movie


class MovieViewSetTestCase(APITestCase):
    def setUp(self):
        # Create a user
        self.user = get_user_model().objects.create_user(
            email="admin@example.com", password="admin"
        )

    def test_create_movie(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("cinema:movie-list")
        data = {"title": "New Movie", "duration": 120}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_movies(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("cinema:movie-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_movie(self):
        self.client.force_authenticate(user=self.user)
        movie = Movie.objects.create(title="Test Movie", duration=120)
        url = reverse("cinema:movie-detail", kwargs={"pk": movie.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
