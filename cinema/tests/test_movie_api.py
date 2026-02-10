from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, Genre, Actor
from cinema.serializers import (
    MovieSerializer,
    MovieListSerializer,
    MovieDetailSerializer
)


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


class UnauthenticatedMovieAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauth_create_movie(self):
        payload = {
            "title": "Unathorized User",
            "description": "Unauthorized description",
            "duration": 1111
        }
        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_movie_detail_for_unauth(self):
        movie = sample_movie()
        genre = sample_genre(name="Action")
        actor = sample_actor(
            first_name="Arnold",
            last_name="Schwarzenegger"
        )

        movie.genres.add(genre)
        movie.actors.add(actor)

        url = reverse("cinema:movie-detail", args=[movie.id])
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test_user@example.com",
            password="testpass123",
        )
        self.client.force_authenticate(self.user)

    def test_movies_list(self):
        sample_movie()
        movie = sample_movie(title="Another movie")

        genre = sample_genre(name="Comedy")
        actor = sample_actor()

        movie.genres.add(genre)
        movie.actors.add(actor)

        res = self.client.get(MOVIE_URL)
        print(res)

        movies = Movie.objects.all()
        serializer = MovieSerializer(movies, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 2)
        self.assertEqual(
            res.data["results"][0]["title"],
            serializer.data[0]["title"]
        )
        self.assertEqual(
            res.data["results"][1]["title"],
            serializer.data[1]["title"]
        )

    def test_filter_movie_list_by_title(self):
        filter_title = "Special title"
        movie = sample_movie(title=filter_title)

        res = self.client.get(
            MOVIE_URL,
            {
                "title": filter_title
            }
        )

        serializer_filtered = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer_filtered.data, res.data["results"])

    def test_movie_list_with_genres(self):
        undefined_genre_movie = sample_movie()

        movie_with_genre_1 = sample_movie()
        movie_with_genre_2 = sample_movie()

        genre_1 = Genre.objects.create(name="Drama")
        genre_2 = Genre.objects.create(name="Comedy")

        movie_with_genre_1.genres.add(genre_1)
        movie_with_genre_2.genres.add(genre_2)

        res = self.client.get(
            MOVIE_URL,
            {
                "genres": f"{genre_1.id}, {genre_2.id}"
            }
        )

        serializer_no_genres_movie = MovieListSerializer(undefined_genre_movie)
        serializer_with_genre_1 = MovieListSerializer(movie_with_genre_1)
        serializer_with_genre_2 = MovieListSerializer(movie_with_genre_2)

        self.assertIn(serializer_with_genre_1.data, res.data["results"])
        self.assertIn(serializer_with_genre_2.data, res.data["results"])
        self.assertNotIn(
            serializer_no_genres_movie.data,
            res.data["results"]
        )

    def test_movie_list_with_actors(self):
        movie_without_actors = sample_movie()

        movie_with_actor_arnold = sample_movie(title="Termiantor")
        movie_with_actor_silvester = sample_movie(title="Rembo: First Blood")

        actor_arnold = sample_actor(
            first_name="Arnold",
            last_name="Schwarzenegger"
        )
        actor_silvester = sample_actor(
            first_name="Silvester",
            last_name="Stalone"
        )

        movie_with_actor_arnold.actors.add(actor_arnold)
        movie_with_actor_silvester.actors.add(actor_silvester)

        res = self.client.get(
            MOVIE_URL,
            {
                "actors": f"{actor_arnold.id}, {actor_silvester.id}"
            }
        )

        serializer_without_actors = MovieListSerializer(movie_without_actors)
        serializer_with_arnold = MovieListSerializer(movie_with_actor_arnold)
        serializer_with_silvester = MovieListSerializer(
            movie_with_actor_silvester
        )

        self.assertIn(serializer_with_arnold.data, res.data["results"])
        self.assertIn(serializer_with_silvester.data, res.data["results"])
        self.assertNotIn(
            serializer_without_actors.data,
            res.data["results"]
        )

    def test_retrieve_movie_list(self):
        movie = sample_movie()
        genre = sample_genre(name="Action")
        actor = sample_actor(
            first_name="Arnold",
            last_name="Schwarzenegger"
        )

        movie.genres.add(genre)
        movie.actors.add(actor)

        url = reverse("cinema:movie-detail", args=[movie.id])
        res = self.client.get(url)
        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Forbidden",
            "description": "Forbidden create movie",
            "duration": 1
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_upload_image_forbidden(self):
        image_url = "http://127.0.0.1:8000/api/uploads/images/1.png"

        res = self.client.post(
            MOVIE_URL,
            {
                "image": image_url
            }
        )

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            email="test_admin@example.com",
            password="AdminTest123",
            is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        payload = {
            "title": "Some Title",
            "description": "Some Movie Desription",
            "duration": 10
        }
        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(id=res.data["id"])
        for key in payload.keys():
            self.assertEqual(payload[key], getattr(movie, key))
        movie = Movie.objects.get(id=res.data["id"])
        for key in payload.keys():
            self.assertEqual(payload[key], getattr(movie, key))

    def test_create_movie_with_genres_and_actors(self):
        genre = Genre.objects.create(name="Action")
        actor = Actor.objects.create(
            first_name="Arnold",
            last_name="Schwarzenegger"
        )

        payload = {
            "title": "Terminator 2",
            "description": "Sequel of Terminator movie",
            "duration": 123,
            "genres": [genre.id],
            "actors": [actor.id]
        }
        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(id=res.data["id"])
        genres = movie.genres.all()
        actors = movie.actors.all()
        self.assertIn(genre, genres)
        self.assertIn(actor, actors)
        self.assertEqual(genres.count(), 1)
        self.assertEqual(actors.count(), 1)
