from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

User = get_user_model()


class MovieViewSetTests(APITestCase):

    def setUp(self):
        self.client = APIClient()

        self.genre1 = Genre.objects.create(name="Action")
        self.genre2 = Genre.objects.create(name="Comedy")
        self.actor1 = Actor.objects.create(first_name="John", last_name="Doe")
        self.actor2 = Actor.objects.create(first_name="Jane", last_name="Doe")

        self.movie = Movie.objects.create(
            title="Movie 1", description="Description of movie 1", duration=120
        )
        self.movie.genres.set([self.genre1, self.genre2])
        self.movie.actors.set([self.actor1, self.actor2])

        self.movie2 = Movie.objects.create(
            title="Movie 2", description="Description of movie 2", duration=90
        )
        self.movie2.genres.set([self.genre1])
        self.movie2.actors.set([self.actor1])

        self.user = User.objects.create_user(
            email="test@user.com", password="testpassword", is_staff=True
        )
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

    def test_list_movies_unauthorized(self):
        self.client.credentials()
        response = self.client.get(reverse("cinema:movie-list"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_movies_authorized(self):
        response = self.client.get(reverse("cinema:movie-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        serializer = MovieListSerializer([self.movie, self.movie2], many=True)
        self.assertEqual(response.data, serializer.data)

    def test_filter_movies_by_title(self):
        response = self.client.get(reverse("cinema:movie-list"), {"title": "Movie 1"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Movie 1")

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
        self.assertEqual(response.data[0]["title"], "Movie 1")

    def test_retrieve_movie(self):
        response = self.client.get(
            reverse("cinema:movie-detail", kwargs={"pk": self.movie.id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        serializer = MovieDetailSerializer(self.movie)
        self.assertEqual(response.data, serializer.data)

    def test_create_movie_authorized(self):
        data = {
            "title": "New Movie",
            "description": "New description",
            "duration": 100,
            "genres": [self.genre1.id],
            "actors": [self.actor1.id],
        }
        response = self.client.post(reverse("cinema:movie-list"), data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Movie.objects.count(), 3)
        self.assertEqual(Movie.objects.get(id=response.data["id"]).title, "New Movie")

    def test_create_movie_unauthorized(self):
        self.client.credentials()
        data = {
            "title": "New Movie",
            "description": "New description",
            "duration": 100,
            "genres": [self.genre1.id],
            "actors": [self.actor1.id],
        }
        response = self.client.post(reverse("cinema:movie-list"), data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
