from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, Genre, Actor


class MovieViewSetTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@myproject.com", "password", is_staff=True
        )
        self.client.force_authenticate(self.user)

        self.genre1 = Genre.objects.create(name="Action")
        self.genre2 = Genre.objects.create(name="Comedy")

        self.actor1 = Actor.objects.create(first_name="John", last_name="Doe")
        self.actor2 = Actor.objects.create(first_name="Jane", last_name="Smith")

        self.movie1 = Movie.objects.create(
            title="Movie 1", description="Description 1", duration=120
        )
        self.movie1.genres.add(self.genre1)
        self.movie1.actors.add(self.actor1)

        self.movie2 = Movie.objects.create(
            title="Movie 2", description="Description 2", duration=90
        )
        self.movie2.genres.add(self.genre2)
        self.movie2.actors.add(self.actor2)

        self.list_url = reverse("cinema:movie-list")
        self.detail_url = lambda pk: reverse("cinema:movie-detail", args=[pk])

    def test_list_movies(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_list_movies_with_filter(self):
        response = self.client.get(self.list_url, {"title": "Movie 1"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Movie 1")

        response = self.client.get(self.list_url, {"genres": str(self.genre1.id)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Movie 1")

    def test_retrieve_movie_detail(self):
        response = self.client.get(self.detail_url(self.movie1.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "Movie 1")
        self.assertEqual(response.data["genres"][0]["name"], "Action")
        self.assertEqual(response.data["actors"][0]["full_name"], "John Doe")

    def test_create_movie(self):
        payload = {
            "title": "Movie 3",
            "description": "Description 3",
            "duration": 150,
            "genres": [self.genre1.id],
            "actors": [self.actor1.id, self.actor2.id],
        }
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Movie.objects.count(), 3)
        self.assertEqual(Movie.objects.last().title, "Movie 3")

    def test_filter_movies_by_actor(self):
        response = self.client.get(self.list_url, {"actors": str(self.actor1.id)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Movie 1")
