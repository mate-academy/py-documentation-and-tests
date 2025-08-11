from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer


class MovieUnauthenticatedTest(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.genre = Genre.objects.create(name="Action")
        self.actor = Actor.objects.create(first_name="John", last_name="Doe")

    def test_movie_list_unauthenticated(self):
        self.client.credentials()
        response = self.client.get(reverse("cinema:movie-list"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_movie_unauthenticated(self):
        self.client.credentials()
        data = {
            "title": "The best movie",
            "description": "description to the best movie",
            "duration": 100,
            "genres": [self.genre.id],
            "actors": [self.actor.id],
        }
        response = self.client.post(reverse("cinema:movie-list"), data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class MovieTest(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.genre1 = Genre.objects.create(name="Horror")
        self.genre2 = Genre.objects.create(name="Action")
        self.actor1 = Actor.objects.create(first_name="John", last_name="Doe")
        self.actor2 = Actor.objects.create(first_name="Anna", last_name="Doe")

        self.movie1 = Movie.objects.create(
            title="Test movie", description="Test description", duration=90
        )
        self.movie2 = Movie.objects.create(
            title="Test movie 2", description="Test description 2", duration=100
        )
        self.movie1.genres.set([self.genre1, self.genre2])
        self.movie1.actors.set([self.actor1, self.actor2])

        self.movie2.genres.set([self.genre1])
        self.movie2.actors.set([self.actor1])

        self.user = get_user_model().objects.create_user(
            email="test.user@mail.com", password="testpassword123", is_staff=True
        )
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

    def test_movie_list_authenticated(self):
        response = self.client.get(reverse("cinema:movie-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        serializer = MovieListSerializer([self.movie1, self.movie2], many=True)
        self.assertEqual(response.data, serializer.data)

    def test_filter_movies_by_title(self):
        response = self.client.get(reverse("cinema:movie-list"), {"title": "2"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Test movie 2")

    def test_filter_movies_by_genres(self):
        response = self.client.get(
            reverse("cinema:movie-list"),
            {"genres": f"{self.genre1.id},{self.genre2.id}"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_filter_movies_by_actors(self):
        response = self.client.get(
            reverse("cinema:movie-list"),
            {"actors": f"{self.actor1.id},{self.actor2.id}"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]["title"], "Test movie")

    def test_retrieve_movie(self):
        response = self.client.get(
            reverse("cinema:movie-detail", kwargs={"pk": self.movie1.id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        serializer = MovieDetailSerializer(self.movie1)
        self.assertEqual(response.data, serializer.data)

    def test_create_movie_authenticated(self):
        data = {
            "title": "The best movie",
            "description": "description to the best movie",
            "duration": 120,
            "genres": [self.genre1.id],
            "actors": [self.actor1.id],
        }
        response = self.client.post(reverse("cinema:movie-list"), data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Movie.objects.count(), 3)
        self.assertEqual(Movie.objects.get(id=response.data["id"]).title, "The best movie")
