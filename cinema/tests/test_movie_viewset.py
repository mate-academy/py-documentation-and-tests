from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from rest_framework_simplejwt.tokens import RefreshToken

from cinema.models import Movie, Genre, Actor
from user.models import User


class MovieViewSetTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="user@test.com", password="testpass123")
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        self.genre1 = Genre.objects.create(name="Action")
        self.genre2 = Genre.objects.create(name="Drama")
        self.actor1 = Actor.objects.create(first_name="John", last_name="Doe")
        self.actor2 = Actor.objects.create(first_name="Jane", last_name="Smith")

        self.movie1 = Movie.objects.create(
            title="Action Movie", description="An action-packed movie", duration=120
        )
        self.movie1.genres.add(self.genre1)
        self.movie1.actors.add(self.actor1)

        self.movie2 = Movie.objects.create(
            title="Dramatic Story", description="A dramatic story", duration=90
        )
        self.movie2.genres.add(self.genre2)
        self.movie2.actors.add(self.actor2)

        self.movie3 = Movie.objects.create(
            title="Mixed Genre", description="Action and drama", duration=110
        )
        self.movie3.genres.add(self.genre1, self.genre2)
        self.movie3.actors.add(self.actor1, self.actor2)

    def test_list_movies(self):
        url = reverse("cinema:movie-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

    def test_filter_movies_by_title(self):
        url = reverse("cinema:movie-list") + "?title=Action"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(any("Action Movie" in movie["title"] for movie in response.data))
        self.assertLessEqual(len(response.data), 3)

    def test_filter_movies_by_genres(self):
        url = reverse("cinema:movie-list") + f"?genres={self.genre2.id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_titles = [movie["title"] for movie in response.data]
        self.assertIn("Dramatic Story", returned_titles)
        self.assertIn("Mixed Genre", returned_titles)

    def test_filter_movies_by_actors(self):
        url = reverse("cinema:movie-list") + f"?actors={self.actor1.id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_titles = [movie["title"] for movie in response.data]
        self.assertIn("Action Movie", returned_titles)
        self.assertIn("Mixed Genre", returned_titles)

    def test_retrieve_movie_detail(self):
        url = reverse("cinema:movie-detail", args=[self.movie1.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "Action Movie")
        self.assertIn("Action", [genre["name"] for genre in response.data["genres"]])

    def test_unauthorized_requests_are_throttled(self):
        self.client.credentials()
        url = reverse("cinema:movie-list")
        for _ in range(10):
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
