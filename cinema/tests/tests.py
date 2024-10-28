from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from cinema.models import Movie


class MovieTests(APITestCase):
    def test_movie_detail(self):
        # Create a sample movie
        movie = Movie.objects.create(title="Sample Movie", description="A test movie", duration=120)

        # Use the movie's id or title if that’s the argument expected by the URL
        url = reverse("movie-detail", args=[movie.title])

        # Make a GET request to the movie detail endpoint
        response = self.client.get(url)

        # Assert that the response contains the correct movie data
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["title"], movie.title)


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
        movie = Movie.objects.create(title="Sample Movie", description="A test movie", duration=120)
        # Create a sample movie here, then test retrieving it
        url = reverse("movie-detail", args=[movie.title])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_movie_filters(self):
        url = f"{reverse('movie-list')}?title=Sample"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
