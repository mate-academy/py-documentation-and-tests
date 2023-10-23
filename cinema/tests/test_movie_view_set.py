from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer
from cinema.tests.test_movie_api import sample_movie, detail_url

MOVIE_URL = reverse("cinema:movie-list")


class UnauthenticatedMovieApiTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@mate.com",
            "secretpass",
        )
        self.client.force_authenticate(self.user)

    def test_list_movies(self):
        sample_movie()
        sample_movie_with_genre = sample_movie()
        sample_movie_with_actors = sample_movie()

        genre = Genre.objects.create(name="Test Genre")
        actor = Actor.objects.create(first_name="Bob", last_name="Test")

        sample_movie_with_genre.genres.add(genre)
        sample_movie_with_actors.actors.add(actor)

        res = self.client.get(MOVIE_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_title(self):
        movie1 = sample_movie(title="First movie")
        movie2 = sample_movie(title="Second movie")
        movie3 = sample_movie(title="Movie without genre")

        genre1 = Genre.objects.create(name="First Genre")
        genre2 = Genre.objects.create(name="Second Genre")

        movie1.genres.add(genre1)
        movie2.genres.add(genre2)

        res = self.client.get(
            MOVIE_URL, {"genres": f"{genre1.id},{genre2.id}"}
        )

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie3)

        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_filter_movies_by_actor(self):
        movie1 = sample_movie(title="First movie")
        movie2 = sample_movie(title="Second movie")
        movie3 = sample_movie(title="Movie without actor")

        actor1 = Actor.objects.create(first_name="Bob", last_name="Test")
        actor2 = Actor.objects.create(first_name="Ann", last_name="Test")

        movie1.actors.add(actor1)
        movie2.actors.add(actor2)

        res = self.client.get(
            MOVIE_URL, {"actors": f"{actor1.id},{actor2.id}"}
        )

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie3)

        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_filter_movies_by_titles(self):
        movie1 = sample_movie(title="First movie")
        movie2 = sample_movie(title="Second movie")

        res = self.client.get(MOVIE_URL, {"title": f"{movie1.title}"})

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)

        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

    def test_retrieve_movie_detail(self):
        movie1 = sample_movie(title="First movie")
        actor1 = Actor.objects.create(first_name="Bob", last_name="Test")
        genre1 = Genre.objects.create(name="First Genre")

        movie1.actors.add(actor1)
        movie1.genres.add(genre1)

        url = detail_url(movie1.id)

        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie1)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Another movie",
            "description": "Some description",
            "duration": 91,
        }

        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test_admin@mate.com",
            "secretAdminPass",
            is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        payload = {
            "title": "Another movie",
            "description": "Some description",
            "duration": 91,
        }

        res = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_create_movie_with_actors_and_genres(self):
        actor1 = Actor.objects.create(first_name="Bob", last_name="Test")
        actor2 = Actor.objects.create(first_name="Ann", last_name="Test")
        genre1 = Genre.objects.create(name="First Genre")
        genre2 = Genre.objects.create(name="Second Genre")

        payload = {
            "title": "Another movie",
            "description": "Some description",
            "duration": 91,
            "actors": [actor1.id, actor2.id],
            "genres": [genre1.id, genre2.id],
        }

        res = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=res.data["id"])

        genres = movie.genres.all()
        actors = movie.actors.all()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        self.assertEqual(genres.count(), 2)
        self.assertIn(genre1, genres)
        self.assertEqual(actors.count(), 2)
        self.assertIn(actor1, actors)

    def test_put_or_delete_movie_not_allowed(self):
        movie = sample_movie()

        url = detail_url(movie.id)

        res1 = self.client.put(url)
        res2 = self.client.delete(url)

        self.assertEqual(res1.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(res2.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
