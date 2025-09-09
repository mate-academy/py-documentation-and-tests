from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from cinema.models import Movie, Genre, Actor
from django.contrib.auth import get_user_model

User = get_user_model()

class MovieViewSetTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="admin.user@cinema.com", password="1qazcde3"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.genre = Genre.objects.create(name="Action")
        self.actor = Actor.objects.create(first_name="John", last_name="Doe")
        self.movie = Movie.objects.create(
            title="Test Movie", description="Desc", duration=120
        )
        self.movie.genres.add(self.genre)
        self.movie.actors.add(self.actor)

    def test_list_movies(self):
        url = reverse("cinema:movie-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_filter_movies_by_title(self):
        url = reverse("cinema:movie-list") + "?title=Test"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_filter_movies_by_genres(self):
        url = reverse("cinema:movie-list") + f"?genres={self.genre.id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_filter_movies_by_actors(self):
        url = reverse("cinema:movie-list") + f"?actors={self.actor.id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
