from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from django.contrib.auth import get_user_model

from cinema.models import (
    Movie, Genre, Actor
)


MOVIE_URL = reverse("cinema:movie-list")


class CustomMovieViewSetTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user1@test.com", password="pas1234"
        )
        self.client.force_authenticate(self.user)

        self.genre = Genre.objects.create(name="genre1")
        self.actor = Actor.objects.create(
            first_name="name1",
            last_name="surname1"
        )

        self.movie1 = Movie.objects.create(
            title="interesting movie",
            description="description1",
            duration=120
        )
        self.movie1.genres.add(self.genre)
        self.movie1.actors.add(self.actor)

        self.movie2 = Movie.objects.create(
            title="another movie",
            description="description2",
            duration=150
        )

    def test_list_movies(self):
        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)

        titles = [movie["title"] for movie in res.data]
        self.assertIn(self.movie1.title, titles)
        self.assertIn(self.movie2.title, titles)

    def test_filter_movies_by_title(self):
        res = self.client.get(
            MOVIE_URL, {"title": "interesting movie"}
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], self.movie1.title)

    def test_filter_movies_by_genre(self):
        res = self.client.get(
            MOVIE_URL, {"genres": f"{self.genre.id}"}
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], self.movie1.title)

    def test_filter_movies_by_actor(self):
        res = self.client.get(MOVIE_URL, {"actors": f"{self.actor.id}"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], self.movie1.title)

    def test_create_movie_unauthorized(self):
        self.client.force_authenticate(user=None)
        payload = {
            "title": "restricted movie",
            "description": "not allowed",
            "duration": 90,
        }
        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_movie_detail(self):
        url = reverse("cinema:movie-detail", args=[self.movie1.id])
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["title"], self.movie1.title)
        self.assertEqual(res.data["description"], self.movie1.description)

    def test_list_action_uses_list_serializer(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("title", res.data[0])

    def test_retrieve_action_uses_detail_serializer(self):
        url = reverse("cinema:movie-detail", args=[self.movie1.id])
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("description", res.data)
