from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from django.contrib.auth import get_user_model


class MovieViewSetTestCase(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "testuser@cinema.com", "password123"
        )
        self.client.force_authenticate(self.user)

    def test_movie_list(self):
        url = reverse("movie-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_movie_detail(self):
        # Create a sample movie here, then test retrieving it
        url = reverse("movie-detail", args=["title"])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_movie_filters(self):
        url = f"{reverse('movie-list')}?title=Sample"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
