from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient
from cinema.models import Movie, Genre, Actor
from django.contrib.auth import get_user_model

MOVIE_URL = reverse("cinema:movie-list")


def create_movie(**params):
    """Допоміжна функція для створення фільму"""
    return Movie.objects.create(**params)


class PrivateMovieApiTests(TestCase):
    """Тести для авторизованих користувачів"""

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="testuser@mail.com", password="testpass"
        )
        self.client.force_authenticate(self.user)

        # Створення жанрів та акторів для фільму
        self.genre1 = Genre.objects.create(name="Action")
        self.genre2 = Genre.objects.create(name="Drama")
        self.actor1 = Actor.objects.create(first_name="John", last_name="Doe")
        self.actor2 = Actor.objects.create(first_name="Jane", last_name="Smith")

    def test_retrieve_movies(self):
        """Тест: отримання списку фільмів"""
        create_movie(
            title="Test Movie 1",
            description="Some description",
            duration=120,
        )
        create_movie(
            title="Test Movie 2",
            description="Another description",
            duration=150,
        )

        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)
