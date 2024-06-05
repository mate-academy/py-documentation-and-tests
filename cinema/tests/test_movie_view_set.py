from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")


def sample_movie(**params) -> Movie:
    default = {
        "title": "Sample Movie",
        "description": "Sample description",
        "duration": 120,
    }
    default.update(params)
    movie = Movie.objects.create(**default)
    return movie


def movie_detail(movie_id: int):
    return reverse("cinema:movie-detail", args=[movie_id])


class UnauthenticatedTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_unauthenticated(self):
        response = self.client.get(MOVIE_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com", password="<PASSWORD>123"
        )
        self.client.force_authenticate(self.user)

        movie_1 = sample_movie(title="test")
        self.genre = Genre.objects.create(name="Sample genre")
        self.actor = Actor.objects.create(
            first_name="Sample first_name",
            last_name="Sample last_name",
        )
        movie_1.genres.set([self.genre])
        movie_1.actors.set([self.actor])
        movie_1.save()

        self.movie_1 = movie_1

        movie_2 = sample_movie()
        self.genre_2 = Genre.objects.create(name="Sample genre 2")
        self.actor_2 = Actor.objects.create(
            first_name="Sample first_name 2",
            last_name="Sample last_name 2",
        )
        movie_2.genres.set([self.genre_2])
        movie_2.actors.set([self.actor_2])
        movie_2.save()

        self.movie_2 = movie_2

    def test_authenticated(self):
        response = self.client.get(MOVIE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_movie_list(self):
        response = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_movie_detail(self):
        response = self.client.get(movie_detail(self.movie_1.id))
        serializer = MovieDetailSerializer(self.movie_1, many=False)
        self.assertEqual(response.data, serializer.data)

    def test_movie_filter_by_title(self):
        response = self.client.get(MOVIE_URL, {"title": f"{self.movie_2.title}"})
        serializer_1 = MovieListSerializer(self.movie_1, many=False)
        serializer_2 = MovieListSerializer(self.movie_2, many=False)

        self.assertIn(serializer_2.data, response.data)

    def test_movie_filter_by_genres(self):
        movie_3 = sample_movie()
        genre_3 = Genre.objects.create(name="genre_3")
        movie_3.genres.set([genre_3])
        movie_3.save()

        serializer_3 = MovieListSerializer(movie_3, many=False)

        serializer_1 = MovieListSerializer(self.movie_1, many=False)
        serializer_2 = MovieListSerializer(self.movie_2, many=False)

        response = self.client.get(
            MOVIE_URL, {"genres": f"{self.genre_2.id}, {self.genre.id}"}
        )

        self.assertIn(serializer_1.data, response.data)
        self.assertIn(serializer_2.data, response.data)
        self.assertNotIn(serializer_3.data, response.data)

    def test_movie_filter_by_actors(self):
        movie_3 = sample_movie()
        actor_3 = Actor.objects.create(first_name="<NAME>", last_name="<NAME>")
        movie_3.actors.set([actor_3])
        movie_3.save()

        serializer_3 = MovieListSerializer(movie_3, many=False)

        serializer_1 = MovieListSerializer(self.movie_1, many=False)
        serializer_2 = MovieListSerializer(self.movie_2, many=False)

        response = self.client.get(
            MOVIE_URL, {"actors": f"{self.actor.id}, {self.actor_2.id}"}
        )

        self.assertIn(serializer_1.data, response.data)
        self.assertIn(serializer_2.data, response.data)
        self.assertNotIn(serializer_3.data, response.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Test title",
            "description": "Test description",
            "duration": 123,
            "genres": self.genre_2,
            "actors": self.actor_2,
        }

        response = self.client.post(MOVIE_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com",
            password="<PASSWORD>123",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)
        self.genre = Genre.objects.create(name="Test genre")
        self.actor = Actor.objects.create(
            first_name="Sample first_name",
            last_name="Sample last_name",
        )

    def test_movie_creation_accessed(self):
        payload = {
            "title": "Test title",
            "description": "Test description",
            "duration": 123,
            "genres": [self.genre.id],
            "actors": [self.actor.id],
        }
        response = self.client.post(MOVIE_URL, payload, format="json")
        movie = Movie.objects.get(id=response.data["id"])
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        for key in ["title", "description", "duration"]:
            self.assertEqual(payload[key], getattr(movie, key))
        self.assertIn(self.genre, movie.genres.all())
        self.assertIn(self.actor, movie.actors.all())

    def test_movie_delete_accessed(self):
        movie = Movie.objects.create(
            title="Test title",
            description="description",
            duration=123,
        )
        movie.genres.add(self.genre)
        movie.actors.add(self.actor)
        response = self.client.delete(MOVIE_URL, {"id": movie.id})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
