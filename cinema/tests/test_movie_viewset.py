from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor
from cinema.serializers import MovieDetailSerializer, MovieListSerializer

MOVIE_URL = reverse("cinema:movie-list")
MOVIE_SESSION_URL = reverse("cinema:moviesession-list")


def sample_movie(**params):
    defaults = {
        "title": "Sample movie",
        "description": "Sample description",
        "duration": 90,
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)


def sample_genre(**params):
    defaults = {
        "name": "Drama",
    }
    defaults.update(params)
    return Genre.objects.create(**defaults)


def sample_actor(**params):
    defaults = {"first_name": "George", "last_name": "Clooney"}
    defaults.update(params)
    return Actor.objects.create(**defaults)


def sample_movie_session(**params):
    cinema_hall = CinemaHall.objects.create(
        name="Blue", rows=20, seats_in_row=20
    )
    defaults = {
        "show_time": "2022-06-02 14:00:00",
        "movie": None,
        "cinema_hall": cinema_hall,
    }
    defaults.update(params)
    return MovieSession.objects.create(**defaults)


def image_upload_url(movie_id):
    """Return URL for image upload"""
    return reverse("cinema:movie-upload-image", args=[movie_id])


def detail_url(movie_id):
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
            email="test_user1@test.com",
            password="test_password1",
        )
        self.client.force_authenticate(self.user)

    def test_movie_list(self):
        sample_movie()
        movie_with_genres = sample_movie()
        movie_with_actors = sample_movie()

        genre = sample_genre()
        actor = sample_actor()

        movie_with_genres.genres.add(genre)
        movie_with_actors.actors.add(actor)

        response = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_filter_movies_by_title(self):
        movie_1 = sample_movie(title="Fury")
        movie_2 = sample_movie(title="Fast & Furious")

        response = self.client.get(MOVIE_URL, {"title": "Fur"})

        serializer_1 = MovieListSerializer(movie_1)
        serializer_2 = MovieListSerializer(movie_2)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(serializer_1.data, response.data)
        self.assertIn(serializer_2.data, response.data)

    def test_filter_movies_by_genre(self):
        genre_1 = sample_genre(name="Action")
        genre_2 = sample_genre(name="Horror")

        movie = sample_movie()
        movie_action = sample_movie()
        movie_action_horror = sample_movie()

        movie_action.genres.add(genre_1)
        movie_action_horror.genres.add(genre_1, genre_2)

        response = self.client.get(
            MOVIE_URL,
            {"genres": f"{genre_1.id},{genre_2.id}"}
        )

        serializer = MovieListSerializer(movie)
        serializer_action = MovieListSerializer(movie_action)
        serializer_action_horror = MovieListSerializer(movie_action_horror)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(serializer_action.data, response.data)
        self.assertIn(serializer_action_horror.data, response.data)
        self.assertNotIn(serializer.data, response.data)

    def test_filter_movies_by_actor(self):
        actor_1 = sample_actor()
        actor_2 = sample_actor()

        movie = sample_movie()
        movie_actor_1 = sample_movie()
        movie_actor_2 = sample_movie()

        movie_actor_1.actors.add(actor_1)
        movie_actor_2.actors.add(actor_2)

        response = self.client.get(
            MOVIE_URL,
            {"actors": f"{actor_1.id},{actor_2.id}"}
        )

        serializer = MovieListSerializer(movie)
        serializer_actor_1 = MovieListSerializer(movie_actor_1)
        serializer_actor_2 = MovieListSerializer(movie_actor_2)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(serializer_actor_1.data, response.data)
        self.assertIn(serializer_actor_2.data, response.data)
        self.assertNotIn(serializer.data, response.data)

    def test_retrieve_movie(self):
        movie = sample_movie()
        movie.actors.add(sample_actor())
        movie.genres.add(sample_genre())

        response = self.client.get(detail_url(movie.id))

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "TestTitle",
            "description": "TestDescription",
            "duration": 150,
        }
        response = self.client.post(MOVIE_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_movie_forbidden(self):
        movie = sample_movie()
        payload = {
            "title": "TestUpdateTitle",
            "description": "TestUpdateDescription",
            "duration": 200,
        }
        response = self.client.put(detail_url(movie.id), payload)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_partial_update_movie_forbidden(self):
        movie = sample_movie()
        payload = {
            "title": "TestUpdateTitle",
        }
        response = self.client.patch(detail_url(movie.id), payload)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_movie_forbidden(self):
        movie = sample_movie()
        response = self.client.delete(detail_url(movie.id))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test_admin1@test.com",
            password="test_password1",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        actor_1 = sample_actor()
        actor_2 = sample_actor()

        genre_1 = sample_genre(name="Action")
        genre_2 = sample_genre(name="Horror")

        payload = {
            "title": "TestTitle",
            "description": "TestDescription",
            "duration": 150,
            "actors": [actor_1.id, actor_2.id],
            "genres": [genre_1.id, genre_2.id],
        }
        response = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(id=response.data["id"])
        actors = movie.actors.all()
        genres = movie.genres.all()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(payload["title"], getattr(movie, "title"))
        self.assertEqual(payload["description"], getattr(movie, "description"))
        self.assertEqual(payload["duration"], getattr(movie, "duration"))
        self.assertIn(actor_1, actors)
        self.assertIn(actor_2, actors)
        self.assertEqual(actors.count(), 2)
        self.assertIn(genre_1, genres)
        self.assertIn(genre_2, genres)
        self.assertEqual(genres.count(), 2)

    def test_delete_movie_not_allowed(self):
        movie = sample_movie()
        response = self.client.delete(detail_url(movie.id))

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED
        )
