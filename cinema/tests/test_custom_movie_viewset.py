from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from django.contrib.auth import get_user_model

from cinema.models import Movie, Genre, Actor


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

        for movie in res.data:
            if movie["title"] == self.movie1.title:
                self.assertEqual(movie["description"], self.movie1.description)
                self.assertEqual(movie["duration"], self.movie1.duration)
            elif movie["title"] == self.movie2.title:
                self.assertEqual(movie["description"], self.movie2.description)
                self.assertEqual(movie["duration"], self.movie2.duration)

    def test_filter_movies_by_title(self):
        movie_title = self.movie1.title
        res = self.client.get(MOVIE_URL, {"title": movie_title})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], movie_title)

    def test_filter_movies_by_genre(self):
        res = self.client.get(
            MOVIE_URL, {"genres": f"{self.genre.id}"}
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], self.movie1.title)

    def test_filter_movies_by_actor(self):
        actor_id = self.actor.id
        res = self.client.get(MOVIE_URL, {"actors": f"{actor_id}"})

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

    def test_create_movie_authorized(self):
        payload = {
            "title": "new movie",
            "description": "new description",
            "duration": 110,
        }
        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["title"], payload["title"])

    def test_retrieve_movie_detail(self):
        url = reverse("cinema:movie-detail", args=[self.movie1.id])
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["title"], self.movie1.title)
        self.assertEqual(res.data["description"], self.movie1.description)

    def test_list_action_uses_list_serializer(self):
        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        expected_fields = ["title", "description", "duration", "genres", "actors"]
        for field in expected_fields:
            self.assertIn(field, res.data[0])

        unexpected_fields = ["created_at", "updated_at"]
        for field in unexpected_fields:
            self.assertNotIn(field, res.data[0])

    def test_retrieve_action_uses_detail_serializer(self):
        url = reverse("cinema:movie-detail", args=[self.movie1.id])
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        expected_fields = ["title", "description", "duration", "genres", "actors"]
        for field in expected_fields:
            self.assertIn(field, res.data)

        unexpected_fields = ["created_at", "updated_at"]
        for field in unexpected_fields:
            self.assertNotIn(field, res.data)
