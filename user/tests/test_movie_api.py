from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")


def detail_url(movie_id: int):
    return reverse("cinema:movie-detail", args=[movie_id])


class UnauthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedBusApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@test.com",
            "testpass",
        )
        self.client.force_authenticate(self.user)

        movie1 = Movie.objects.create(
            title="Test movie 1",
            description="Test",
            duration=120
        )
        movie2 = Movie.objects.create(
            title="Test movie 2",
            description="Test",
            duration=150
        )
        movie3 = Movie.objects.create(
            title="Test movie 3",
            description="Test",
            duration=180
        )

        genre1 = Genre.objects.create(name="test_genre1")
        genre2 = Genre.objects.create(name="test_genre2")
        genre3 = Genre.objects.create(name="test_genre3")

        movie1.genres.add(genre1, genre2)
        movie2.genres.add(genre2)
        movie3.genres.add(genre3)

        actor1 = Actor.objects.create(first_name="Test1", last_name="Actor1")
        actor2 = Actor.objects.create(first_name="Test2", last_name="Actor2")
        actor3 = Actor.objects.create(first_name="Test2", last_name="Actor3")

        movie1.actors.add(actor1, actor3)
        movie2.actors.add(actor2)
        movie3.actors.add(actor3)


    def test_list_movies(self):
        res = self.client.get(MOVIE_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_genres(self):
        genre1 = Genre.objects.get(id=1)
        genre2 = Genre.objects.get(id=2)

        res = self.client.get(MOVIE_URL, {"genres": f"{genre1.id},{genre2.id}"})

        serializer1 = MovieListSerializer(Movie.objects.get(id=1))
        serializer2 = MovieListSerializer(Movie.objects.get(id=2))
        serializer3 = MovieListSerializer(Movie.objects.get(id=3))

        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_filter_movies_by_actors(self):
        actor1 = Actor.objects.get(id=1)
        actor2 = Actor.objects.get(id=2)

        res = self.client.get(MOVIE_URL, {"actors": f"{actor1.id},{actor2.id}"})

        serializer1 = MovieListSerializer(Movie.objects.get(id=1))
        serializer2 = MovieListSerializer(Movie.objects.get(id=2))
        serializer3 = MovieListSerializer(Movie.objects.get(id=3))

        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_filter_movies_by_title(self):
        res = self.client.get(MOVIE_URL, {"title": "movie 2"})

        serializer1 = MovieListSerializer(Movie.objects.get(id=1))
        serializer2 = MovieListSerializer(Movie.objects.get(id=2))
        serializer3 = MovieListSerializer(Movie.objects.get(id=3))

        self.assertNotIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_retrieve_movie_detail(self):
        movie = Movie.objects.create(title="Movie_retrieve", description="Test", duration=120)
        movie.genres.add(Genre.objects.get(id=1))
        movie.actors.add(Actor.objects.get(id=1))
        url = detail_url(movie.id)
        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Test movie",
            "description": "Create test movie",
            "duration": 100,
            "genres": 1,
            "actors": 2,
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_movie_forbidden(self):
        movie = Movie.objects.get(id=1)
        url = detail_url(movie.id)

        payload = {
            "title": "Test movie",
            "description": "Create test movie",
            "duration": 100,
        }

        res = self.client.put(url, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_partial_update_movie_forbidden(self):
        movie = Movie.objects.get(id=1)
        url = detail_url(movie.id)

        payload = {
            "description": "Create test movie",
        }

        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_movie_forbidden(self):
        movie = Movie.objects.get(id=1)
        url = detail_url(movie.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminBusApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@test.com",
            "testpass",
            is_staff=True
        )
        self.client.force_authenticate(self.user)

        Movie.objects.create(
            title="Test movie",
            description="Test",
            duration=120
        )

    def test_create_movie(self):
        payload = {
            "title": "Test movie",
            "description": "Create test movie",
            "duration": 100,
        }

        res = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_update_movie_not_allowed(self):
        movie = Movie.objects.get(id=1)
        url = detail_url(movie.id)

        payload = {
            "title": "Test updated movie",
            "description": "Update test movie",
            "duration": 120,
        }

        res = self.client.put(url, payload)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_partial_update_movie_not_allowed(self):
        movie = Movie.objects.get(id=1)
        url = detail_url(movie.id)

        payload = {
            "description": "Update test movie",
        }

        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_movie_not_allowed(self):
        movie = Movie.objects.get(id=1)
        url = detail_url(movie.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
