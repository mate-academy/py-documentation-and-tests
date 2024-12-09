from django.contrib.auth import get_user_model

from django.test import TestCase

from rest_framework import status

from rest_framework.reverse import reverse

from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor

from cinema.serializers import MovieDetailSerializer, MovieListSerializer

from cinema.tests.test_movie_api import MOVIE_URL


class UnAuthenticatedMovieAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(MOVIE_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieAPITests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create(
            email="test@user.com", password="test-1-2-3"
        )
        self.client.force_authenticate(self.user)

    def test_get_movie_list(self):

        response = self.client.get(MOVIE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_user_forbidden_to_create_movie(self):

        payload = {
            "title": "test",
            "description": "test",
            "duration": 123,
        }

        response = self.client.post(MOVIE_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_filter_movie_by_genre(self):
        movie = Movie.objects.create(
            title="test",
            description="test",
            duration=123,
        )
        genre = Genre.objects.create(name="test")

        movie.genres.add(genre)

        response = self.client.get(MOVIE_URL, {"genre": genre.id})

        serializer = MovieListSerializer(movie)

        self.assertIn(serializer.data, response.data)

    def test_filter_movie_by_actor(self):
        movie = Movie.objects.create(
            title="test",
            description="test",
            duration=123,
        )
        actor = Actor.objects.create(
            first_name="test",
            last_name="test",
        )

        movie.actors.add(actor)

        response = self.client.get(MOVIE_URL, {"actors": actor.id})

        serializer = MovieListSerializer(movie)
        self.assertIn(serializer.data, response.data)

    def test_retrieve_movie(self):
        movie = Movie.objects.create(
            title="test",
            description="test",
            duration=123,
        )

        genre = Genre.objects.create(name="test")

        actor = Actor.objects.create(
            first_name="test",
            last_name="test",
        )

        movie.genres.add(genre)
        movie.actors.add(actor)

        detail_url = reverse("cinema:movie-detail", args=[movie.id])

        response = self.client.get(detail_url)
        serializer = MovieDetailSerializer(movie)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)


class AdminMovieTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@user.com",
            password="test-1-2-3",
            is_staff=True,
        )

        self.client.force_authenticate(self.user)

    def test_create_movie_allow_for_admin(self):
        payload = {
            "title": "Gang Bang",
            "description": "Super interesting",
            "duration": 123,
        }

        response = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(id=response.data["id"])

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        for key in payload.keys():
            self.assertEqual(payload[key], getattr(movie, key))

    def test_create_movie_with_genres_and_actors_allow_for_admin(self):
        genre_1 = Genre.objects.create(name="test")
        genre_2 = Genre.objects.create(name="test2")

        actor_1 = Actor.objects.create(
            first_name="test_1",
            last_name="test_1",
        )
        actor_2 = Actor.objects.create(
            first_name="test_2",
            last_name="test_2",
        )

        payload = {
            "title": "TMNT",
            "description": "Wonderful cartoon",
            "duration": 123,
            "genres": [genre_1.id, genre_2.id],
            "actors": [actor_1.id, actor_2.id],
        }
        response = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(id=response.data["id"])

        genres = movie.genres.all()
        actors = movie.actors.all()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn(genre_1, genres)
        self.assertIn(genre_2, genres)
        self.assertIn(actor_1, actors)
        self.assertIn(actor_2, actors)
        self.assertEqual(genres.count(), 2)
        self.assertEqual(actors.count(), 2)
