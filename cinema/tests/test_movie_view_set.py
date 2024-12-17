from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient
from django.test import TestCase

from cinema.models import Movie, Genre, Actor


class MovieViewSetTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@gmail.com",
            "testpassword123"
        )
        self.client.force_authenticate(self.user)
        self.genre = Genre.objects.create(
            name="action"
        )
        self.first_actor = Actor.objects.create(
            first_name="John",
            last_name="Doe",
        )
        self.second_actor = Actor.objects.create(
            first_name="Jane",
            last_name="Ron",
        )
        self.first_movie = Movie.objects.create(
            title="First movie",
            description="random text",
            duration=50,
        )
        self.first_movie.actors.add(self.first_actor)
        self.first_movie.genres.add(self.genre)
        self.second_movie = Movie.objects.create(
            title="Second movie",
            description="random text 2",
            duration=50,
        )
        self.second_movie.actors.add(self.second_actor)
        self.second_movie.genres.add(self.genre)

    def test_movie_list(self):
        url = reverse("cinema:movie-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_search_by_title(self):
        url = reverse("cinema:movie-list")
        response = self.client.get(url, data={"title": "First"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], self.first_movie.title)

    def test_search_by_actor(self):
        url = reverse("cinema:movie-list")
        response = self.client.get(url, data={"actors": self.second_actor.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["actors"], ["Jane Ron"])

    def test_search_by_genre(self):
        url = reverse("cinema:movie-list")
        response = self.client.get(url, data={"genres": self.genre.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_detail(self):
        url = reverse("cinema:movie-detail", kwargs={"pk": self.first_movie.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], self.first_movie.title)
        self.assertEqual(response.data["description"], self.first_movie.description)

class MovieViewSetUnAuthorizedTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
    def test_unauthorized(self):
        url = reverse("cinema:movie-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
