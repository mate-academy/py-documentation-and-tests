from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieDetailSerializer, MovieListSerializer

MOVIE_URL = reverse("cinema:movie-list")


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=(movie_id,))


def sample_movie(**params) -> Movie:
    default = {
        "title": "Test",
        "description": "Test Movie API",
        "duration": 30,
    }
    default.update(params)
    return Movie.objects.create(**default)


class UnauthenticatedTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.test",
            password="test",
        )
        self.client.force_authenticate(self.user)

    def test_movie_list(self):
        sample_movie(title="Test")
        movie_with_genres = sample_movie(title="Test2")

        genre_1 = Genre.objects.create(name="Rome")
        genre_2 = Genre.objects.create(name="Horror")
        movie_with_genres.genres.add(genre_1, genre_2)

        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        if "results" in res.data:
            self.assertEqual(res.data["results"], serializer.data)
        else:
            self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_genre(self):
        movie_without_genres = sample_movie(title="Test3")
        movie_with_genres_1 = sample_movie(title="Test4")
        movie_with_genres_2 = sample_movie(title="Test5")

        genre_1 = Genre.objects.create(name="Rome")
        genre_2 = Genre.objects.create(name="Horror")

        movie_with_genres_1.genres.add(genre_1)
        movie_with_genres_2.genres.add(genre_2)

        res = self.client.get(MOVIE_URL, {"genres": f"{genre_1.id}"})

        serializer_without_genres = MovieListSerializer(movie_without_genres)
        serializer_movie_genre_1 = MovieListSerializer(movie_with_genres_1)
        serializer_movie_genre_2 = MovieListSerializer(movie_with_genres_2)

        results = res.data["results"] if "results" in res.data else res.data

        self.assertIn(serializer_movie_genre_1.data, results)
        self.assertNotIn(serializer_without_genres.data, results)
        self.assertNotIn(serializer_movie_genre_2.data, results)

    def test_retrieve_movie_details(self):
        movie = sample_movie()
        movie.genres.add(Genre.objects.create(name="Rome"))

        url = detail_url(movie.id)

        res = self.client.get(url)
        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_retrieve_movie_forbidden(self):

        payload = {
            "title": "Test",
            "description": "Test Movie API",
            "duration": 30,
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@admin.test",
            password="test",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        genre = Genre.objects.create(name="Action")
        actor = Actor.objects.create(first_name="John", last_name="Doe")

        payload = {
            "title": "Test",
            "description": "Test Movie API",
            "duration": 30,
            "genres": [genre.id],
            "actors": [actor.id],
        }
        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Movie.objects.filter(id=res.data["id"]).exists())

    def test_create_movie_with_genre(self):

        genre_1 = Genre.objects.create(name="Rome")
        genre_2 = Genre.objects.create(name="Horror")
        actor_1 = Actor.objects.create(first_name="John", last_name="Doe")
        actor_2 = Actor.objects.create(first_name="JohnD", last_name="DoeD")

        payload = {
            "title": "Test",
            "description": "Test Movie API",
            "duration": 30,
            "genres": [genre_1.id, genre_2.id],
            "actors": [actor_1.id, actor_2.id],
        }
        res = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(id=res.data["id"])
        genres = movie.genres.all()
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn(genre_1, genres)
        self.assertIn(genre_2, genres)
        self.assertEqual(genres.count(), 2)

    def test_delete_movie_not_allowed(self):
        movie = sample_movie()

        url = detail_url(movie.id)

        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
