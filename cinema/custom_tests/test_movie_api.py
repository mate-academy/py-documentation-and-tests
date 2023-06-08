from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from rest_framework.test import APIClient

from cinema.models import Movie, Actor, Genre
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")  # 127.0.0.1:8000/api/cinema/movies/


def sample_movie(**params):
    defaults = {
        "title": "Sample Movie",
        "description": "Sample description",
        "duration": 120,
    }
    defaults.update(params)

    return Movie.objects.create(**defaults)


# 127.0.0.1:8000/api/cinema/movies/{id}/
def detail_url(movie_id: int):
    return reverse("cinema:movie-detail", args=[movie_id])


class UnauthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@test.com",
            "testpass",
        )
        self.client.force_authenticate(self.user)

    def test_list_movies(self):
        sample_movie()
        movie_with_actor_and_genre = sample_movie()

        actor = Actor.objects.create(first_name="Test", last_name="Testich")
        genre = Genre.objects.create(name="Drama")

        movie_with_actor_and_genre.actors.add(actor)
        movie_with_actor_and_genre.genres.add(genre)

        res = self.client.get(MOVIE_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movie_by_title(self):
        movie1 = sample_movie(title="Movie 1")
        movie2 = sample_movie(title="Movie 2")

        res = self.client.get(MOVIE_URL, {"title": movie1.title})

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)

        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

    def test_filter_movie_by_actor(self):
        movie1 = sample_movie(title="Movie 1")
        movie2 = sample_movie(title="Movie 2")

        actor = Actor.objects.create(
            first_name="Test_first", last_name="Test_last"
        )

        movie1.actors.add(actor)

        res = self.client.get(MOVIE_URL, {"actors": actor.id})

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)

        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

    def test_filter_movie_by_genre(self):
        movie1 = sample_movie(title="Movie 1")
        movie2 = sample_movie(title="Movie 2")

        genre = Genre.objects.create(name="Crime")

        movie1.genres.add(genre)

        res = self.client.get(MOVIE_URL, {"genres": genre.id})

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)

        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()

        actor = Actor.objects.create(
            first_name="Test_first", last_name="Test_last"
        )
        genre = Genre.objects.create(name="Crime")

        movie.actors.add(actor)
        movie.genres.add(genre)

        url = detail_url(movie.id)
        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Test title",
            "description": "Test description",
            "duration": 120,
        }

        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@admin.com", "testpass", is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        payload = {
            "title": "Test title",
            "description": "Test description",
            "duration": 120,
        }

        res = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_create_movie_with_actor_and_genre(self):
        actor = Actor.objects.create(
            first_name="Test_first", last_name="Test_last"
        )
        genre = Genre.objects.create(name="Crime")

        payload = {
            "title": "Test title",
            "description": "Test description",
            "duration": 120,
            "actors": actor.id,
            "genres": genre.id,
        }

        res = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=res.data["id"])
        actors = movie.actors.all()
        genres = movie.genres.all()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn(actor, actors)
        self.assertIn(genre, genres)

    def test_put_movie_not_allowed(self):
        movie = sample_movie()

        url = detail_url(movie.id)

        new_payload = {
            "title": "Updated Movie title",
            "description": "Updated description",
            "duration": 100,
        }

        res = self.client.put(url, new_payload)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_movie_not_allowed(self):
        movie = sample_movie()

        url = detail_url(movie.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
