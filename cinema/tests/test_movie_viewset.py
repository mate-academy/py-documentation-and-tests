from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from cinema.models import Movie, Genre, Actor


MOVIES_URL = reverse("cinema:movie-list")


def sample_genre(name="Test"):
    return Genre.objects.create(name=name)


def sample_actor(first_name="John", last_name="Doe"):
    return Actor.objects.create(first_name=first_name, last_name=last_name)


class MovieViewSetTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            "user@example.com", "testpassword"
        )
        self.client.force_authenticate(self.user)

        self.genre1 = sample_genre("Horror")
        self.genre2 = sample_genre("Action")

        self.actor1 = sample_actor("LeBron", "James")
        self.actor2 = sample_actor("Henry", "Kissinger")

        self.movie1 = Movie.objects.create(
            title="Democracy Prophets",
            description="Just a regular freedom-loving boys",
            duration=143
        )
        self.movie1.genres.add(self.genre1)
        self.movie1.actors.add(self.actor1)

        self.movie2 = Movie.objects.create(
            title="Heat", description="Best friends chillin", duration=120
        )
        self.movie2.genres.add(self.genre2)
        self.movie2.actors.add(self.actor2)

    def test_list_movies(self):
        res = self.client.get(MOVIES_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)

    def test_filter_movies_by_title(self):
        res = self.client.get(MOVIES_URL, {"title": "Democracy Prophets"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data[0]["title"], "Democracy Prophets")
        self.assertEqual(len(res.data), 1)

    def test_filter_by_genres(self):
        res = self.client.get(MOVIES_URL, {"genres": f"{self.genre1.id}"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data[0]["title"], self.movie1.title)
        self.assertEqual(len(res.data), 1)

    def test_filter_by_actors(self):
        res = self.client.get(MOVIES_URL, {"actors": f"{self.actor2.id}"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data[0]["title"], self.movie2.title)
        self.assertEqual(len(res.data), 1)

    def test_movie_detail(self):
        url = reverse("cinema:movie-detail", args=[self.movie1.id])
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["title"], self.movie1.title)

    def test_unauthenticated_user_cannot_access_list(self):
        self.client.force_authenticate(user=None)
        res = self.client.get(MOVIES_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
