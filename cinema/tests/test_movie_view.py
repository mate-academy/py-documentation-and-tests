from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from cinema.models import Genre, Movie, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer, MovieSerializer

MOVIE_URL = reverse("cinema:movie-list")


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


def sample_movie(**params) -> Movie:
    defaults = {
        "title": "Sample",
        "description": "",
        "duration": 100,
    }
    defaults.update(params)

    return Movie.objects.create(**defaults)


class UnauthenticatedMovieApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(MOVIE_URL)
        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED
        )


class AuthenticatedMovieApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="testemail@test.test",
            password="testpassword123"
        )
        self.client.force_authenticate(self.user)

        self.actor1 = Actor.objects.create(
            first_name="FirstName1",
            last_name="LastName1",
        )
        self.actor2 = Actor.objects.create(
            first_name="TestFirstName",
            last_name="TestLastName",
        )

        self.genre1 = Genre.objects.create(
            name="Genre11t12t"
        )
        self.genre2 = Genre.objects.create(
            name="TestGenre4214"
        )

    @staticmethod
    def serialize_list_movie(movie: Movie) -> dict:
        return MovieListSerializer(movie).data

    def test_movies_list(self):
        movie_with_actors = sample_movie()
        movie_with_genres = sample_movie()

        movie_with_actors.actors.add(self.actor1, self.actor2)
        movie_with_genres.genres.add(self.genre1, self.genre2)

        response = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_filter_movies_by_title(self):
        movie_with_title = sample_movie(title="Inception")
        movie_without_title = sample_movie(title="Interstellar")

        response = self.client.get(MOVIE_URL, {"title": "Inception"})

        self.assertIn(MovieListSerializer(movie_with_title).data, response.data)
        self.assertNotIn(MovieListSerializer(movie_without_title).data, response.data)

    def test_filter_movies_by_genre(self):
        movie_without_genre = sample_movie()

        movie_with_genre_1 = sample_movie()
        movie_with_genre_1.genres.add(self.genre1)

        movie_with_genre_2 = sample_movie()
        movie_with_genre_2.genres.add(self.genre2)

        response = self.client.get(
            MOVIE_URL,
            {"genres": f"{self.genre1.id},{self.genre2.id}"}
        )

        self.assertIn(self.serialize_list_movie(movie_with_genre_1), response.data)
        self.assertIn(self.serialize_list_movie(movie_with_genre_2), response.data)
        self.assertNotIn(self.serialize_list_movie(movie_without_genre), response.data)

    def test_filter_movies_by_actor(self):
        movie_without_actors = sample_movie()

        movie_with_actor_1 = sample_movie()
        movie_with_actor_1.actors.add(self.actor1)

        movie_with_actor_2 = sample_movie()
        movie_with_actor_2.actors.add(self.actor2)

        response = self.client.get(
            MOVIE_URL,
            {"actors": f"{self.actor1.id},{self.actor2.id}"}
        )

        self.assertIn(self.serialize_list_movie(movie_with_actor_1), response.data)
        self.assertIn(self.serialize_list_movie(movie_with_actor_2), response.data)
        self.assertNotIn(self.serialize_list_movie(movie_without_actors), response.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        movie.actors.add(self.actor1)
        movie.genres.add(self.genre1)

        url = detail_url(movie.id)

        response = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_create_movie_forbidden(self):
        movie_payload = {
            "title": "Test title",
            "description": "Test description",
            "duration": 30,
        }

        response = self.client.post(MOVIE_URL, movie_payload)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="adminuser@test.test",
            password="Adminpassword123",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)

        self.actor1 = Actor.objects.create(
            first_name="FirstName1",
            last_name="LastName1",
        )
        self.actor2 = Actor.objects.create(
            first_name="TestFirstName",
            last_name="TestLastName",
        )

        self.genre1 = Genre.objects.create(
            name="Genre11t12t"
        )
        self.genre2 = Genre.objects.create(
            name="TestGenre4214"
        )

    def test_create_movie(self):
        movie_payload = {
            "title": "Test title",
            "description": "Test description",
            "duration": 30,
        }

        response = self.client.post(MOVIE_URL, movie_payload)

        movie = Movie.objects.get(id=response.data["id"])

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        for key in movie_payload:
            self.assertEqual(movie_payload[key], getattr(movie, key))

    def test_create_movie_with_actors_and_genres(self):
        movie_payload = {
            "title": "Test title",
            "description": "Test description",
            "duration": 30,
            "actors": [self.actor1.id, self.actor2.id],
            "genres": [self.genre1.id, self.genre2.id],
        }

        response = self.client.post(MOVIE_URL, movie_payload)

        movie = Movie.objects.get(id=response.data["id"])

        actors = movie.actors.all()
        genres = movie.genres.all()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertIn(self.actor1, actors)
        self.assertIn(self.actor2, actors)
        self.assertEqual(actors.count(), 2)

        self.assertIn(self.genre1, genres)
        self.assertIn(self.genre2, genres)
        self.assertEqual(genres.count(), 2)

    def test_delete_movie_not_allowed(self):
        movie = sample_movie()

        url = detail_url(movie.pk)

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
