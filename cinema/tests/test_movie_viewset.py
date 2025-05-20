from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from cinema.models import Movie, Genre, Actor


MOVIES_URL = reverse("cinema:movie-list")


def sample_genre(name="Action"):
    return Genre.objects.create(name=name)


def sample_actor(first_name="Tom", last_name="Cruise"):
    return Actor.objects.create(first_name=first_name, last_name=last_name)


class MovieViewSetTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            "user@example.com", "testpass123"
        )
        self.client.force_authenticate(self.user)

        self.genre1 = sample_genre("Action")
        self.genre2 = sample_genre("Comedy")

        self.actor1 = sample_actor("Tom", "Hanks")
        self.actor2 = sample_actor("Will", "Smith")

        self.movie1 = Movie.objects.create(
            title="Avengers", description="Superheroes save the world", duration=143
        )
        self.movie1.genres.add(self.genre1)
        self.movie1.actors.add(self.actor1)

        self.movie2 = Movie.objects.create(
            title="Bad Boys", description="Detectives in Miami", duration=120
        )
        self.movie2.genres.add(self.genre2)
        self.movie2.actors.add(self.actor2)

    def test_list_movies(self):
        res = self.client.get(MOVIES_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)

    def test_filter_movies_by_title(self):
        res = self.client.get(MOVIES_URL, {"title": "Avengers"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data[0]["title"], "Avengers")
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
        self.client.force_authenticate(user=None)  # remove auth
        res = self.client.get(MOVIES_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
