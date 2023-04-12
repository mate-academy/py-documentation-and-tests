from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from rest_framework.test import APIClient

from cinema.models import Movie, Actor, Genre
from cinema.serializers import MovieSerializer

MOVIE_URL = reverse("cinema:movie-list")


class UnauthenticatedMoviesApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMoviesApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user("test@movie.com", "testpass")
        self.client.force_authenticate(self.user)
        self.movie1 = Movie.objects.create(
            title="Movie 1", description="Description 1", duration=100
        )
        self.movie2 = Movie.objects.create(
            title="Movie 2", description="Description 2", duration=120
        )
        self.movie3 = Movie.objects.create(
            title="Movie 3", description="Description 3", duration=90
        )

    def test_list_movies(self):
        response = self.client.get(MOVIE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

    def test_filter_movies_by_title(self):
        response = self.client.get(MOVIE_URL, {"title": "Movie 1"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Movie 1")

    def test_filter_movies_by_genres(self):
        response = self.client.get(MOVIE_URL, {"genres": "1"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)
        genre1 = Genre.objects.create(name="test_genre")
        self.movie1.genres.add(genre1)
        response = self.client.get(MOVIE_URL, {"genres": "1"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Movie 1")

    def test_filter_movies_by_actors(self):
        response = self.client.get(MOVIE_URL, {"actors": "1"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)
        actor1 = Actor.objects.create(
            first_name="actor_test_name", last_name="actor_test_last_name"
        )
        self.movie1.actors.add(actor1)
        response = self.client.get(MOVIE_URL, {"actors": "1"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Movie 1")

    def test_retrieve_movie(self):
        url = reverse("cinema:movie-detail", args=[self.movie1.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "Movie 1")

    def test_create_movie_is_false_from_list(self):
        data = {"title": "New Movie", "description": "New Description", "duration": 120}
        response = self.client.post(MOVIE_URL, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


def sample_genre(name="Action"):
    return Genre.objects.create(name=name)


def sample_actor(first_name="John", last_name="Doe"):
    return Actor.objects.create(first_name=first_name, last_name=last_name)


def sample_movie(**params):
    defaults = {
        "title": "Sample movie",
        "description": "Sample description",
        "duration": 120,
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)


class AdminUserMovieApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@movie.com", "testpass", is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        genres = [sample_genre(), sample_genre(name="Drama")]
        actors = [sample_actor(), sample_actor(first_name="Jane", last_name="Doe")]
        payload = {
            "title": "Test Movie",
            "description": "Test Description",
            "duration": 90,
            "genres": [genre.id for genre in genres],
            "actors": [actor.id for actor in actors],
        }

        response = self.client.post(MOVIE_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(id=response.data["id"])
        serializer = MovieSerializer(movie)
        self.assertEqual(serializer.data, response.data)

    def test_delete_movie_is_not_allowed(self):
        movie = sample_movie()

        url = reverse("cinema:movie-detail", args=[movie.id])
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
