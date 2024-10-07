from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from cinema.models import Movie, Genre, Actor
from django.contrib.auth import get_user_model


class MovieViewSetTestCase(TestCase):
    def setUp(self):
        self.genre1 = Genre.objects.create(name="Action")
        self.genre2 = Genre.objects.create(name="Drama")
        self.actor1 = Actor.objects.create(first_name="John", last_name="Doe")
        self.actor2 = Actor.objects.create(first_name="Jane", last_name="Smith")

        self.movie = Movie.objects.create(
            title="Test Movie", description="Test description", duration=120
        )
        self.movie.genres.add(self.genre1, self.genre2)
        self.movie.actors.add(self.actor1, self.actor2)

        self.admin_user = get_user_model().objects.create_superuser(
            email="admin@test.com", password="adminpass"
        )
        self.user = get_user_model().objects.create_user(
            email="user@test.com", password="userpass"
        )

        self.admin_token = self.get_token_for_user(self.admin_user)
        self.user_token = self.get_token_for_user(self.user)

    def get_token_for_user(self, user):
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)

    def auth_headers(self, token):
        return {
            "HTTP_AUTHORIZATION": f"Bearer {token}",
        }

    def test_list_movies_with_filters(self):
        url = reverse("cinema:movie-list")
        response = self.client.get(
            url,
            {
                "title": "Test",
                "genres": f"{self.genre1.id},{self.genre2.id}",
                "actors": f"{self.actor1.id},{self.actor2.id}",
            },
            **self.auth_headers(self.admin_token),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["title"], "Test Movie")

    def test_get_single_movie(self):
        url = reverse("cinema:movie-detail", args=[self.movie.id])
        response = self.client.get(url, **self.auth_headers(self.admin_token))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["title"], "Test Movie")

    def test_get_queryset_with_title_filter(self):
        url = reverse("cinema:movie-list")
        response = self.client.get(
            url, {"title": "Test"}, **self.auth_headers(self.admin_token)
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)

    def test_get_queryset_with_genre_filter(self):
        url = reverse("cinema:movie-list")
        response = self.client.get(
            url, {"genres": f"{self.genre1.id}"}, **self.auth_headers(self.admin_token)
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)

    def test_get_queryset_with_actor_filter(self):
        url = reverse("cinema:movie-list")
        response = self.client.get(
            url, {"actors": f"{self.actor1.id}"}, **self.auth_headers(self.admin_token)
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)

    def test_get_queryset_no_results(self):
        url = reverse("cinema:movie-list")
        response = self.client.get(
            url, {"title": "Non-existent"}, **self.auth_headers(self.admin_token)
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 0)

    def test_movie_serializer_class_on_list(self):
        url = reverse("cinema:movie-list")
        response = self.client.get(url, **self.auth_headers(self.admin_token))
        self.assertIn("image", response.json()[0])

    def test_movie_serializer_class_on_retrieve(self):
        url = reverse("cinema:movie-detail", args=[self.movie.id])
        response = self.client.get(url, **self.auth_headers(self.admin_token))
        self.assertIn("genres", response.json())
        self.assertIn("actors", response.json())

    def test_create_movie_permission(self):
        self.client.logout()

        url = reverse("cinema:movie-list")
        data = {
            "title": "New Movie",
            "description": "New description",
            "duration": 100,
            "genres": [1],
            "actors":[1],
        }

        response = self.client.post(
            url, data, format="json", **self.auth_headers(self.user_token)
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client.post(
            url, data, format="json", **self.auth_headers(self.admin_token)
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

