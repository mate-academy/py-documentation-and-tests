from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework.reverse import reverse
from django.test import TestCase

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=(movie_id,))


def sample_movie(**params) -> Movie:
    defaults = {
        "title": "Drive",
        "description": "Sample Movie Description",
        "duration": 67,
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)


class UnauthenticatedMovieViewSetTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(MOVIE_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieViewSetTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@mail.com",
            password="testpassword"
        )
        self.client.force_authenticate(self.user)

    def test_movies_list(self):
        sample_movie()
        movie_with_genres_and_actors = sample_movie()

        genre = Genre.objects.create(name="Action")
        genre2 = Genre.objects.create(name="Story")

        actor = Actor.objects.create(first_name="John", last_name="Doe")
        actor2 = Actor.objects.create(first_name="Jane", last_name="Doe")

        movie_with_genres_and_actors.genres.add(genre, genre2)
        movie_with_genres_and_actors.actors.add(actor, actor2)

        response = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_filter_movies_by_title(self):
        movie = sample_movie()
        movie2 = sample_movie(title="Titanic")

        response = self.client.get(
            MOVIE_URL,
            {"title": f"{movie.title}"}
        )
        serializer = MovieListSerializer(movie)
        serializer2 = MovieListSerializer(movie2)

        self.assertIn(serializer.data, response.data)
        self.assertNotIn(serializer2.data, response.data)

    def test_filter_movies_by_genres(self):
        movie_without_genres = sample_movie()
        movie_with_genre1 = sample_movie(title="Titanic")
        movie_with_genre2 = sample_movie(title="Bell")

        genre = Genre.objects.create(name="Action")
        genre2 = Genre.objects.create(name="Story")

        movie_with_genre1.genres.add(genre)
        movie_with_genre2.genres.add(genre2)

        response = self.client.get(
            MOVIE_URL,
            {"genres": f"{genre.id},{genre2.id}"}
        )
        serializer_without_genres = MovieListSerializer(movie_without_genres)
        serializer_movie_genre1 = MovieListSerializer(movie_with_genre1)
        serializer_movie_genre2 = MovieListSerializer(movie_with_genre2)

        self.assertIn(serializer_movie_genre1.data, response.data)
        self.assertIn(serializer_movie_genre2.data, response.data)
        self.assertNotIn(serializer_without_genres.data, response.data)

    def test_filter_movies_by_actors(self):
        movie_without_actors = sample_movie()
        movie_with_actor1 = sample_movie(title="Titanic")
        movie_with_actor2 = sample_movie(title="Bell")

        actor = Actor.objects.create(first_name="John", last_name="Doe")
        actor2 = Actor.objects.create(first_name="Jane", last_name="Doe")

        movie_with_actor1.actors.add(actor)
        movie_with_actor2.actors.add(actor2)

        response = self.client.get(
            MOVIE_URL,
            {"actors": f"{actor.id},{actor2.id}"}
        )
        serializer_without_actors = MovieListSerializer(movie_without_actors)
        serializer_movie_actor1 = MovieListSerializer(movie_with_actor1)
        serializer_movie_actor2 = MovieListSerializer(movie_with_actor2)

        self.assertNotIn(serializer_without_actors.data, response.data)
        self.assertIn(serializer_movie_actor1.data, response.data)
        self.assertIn(serializer_movie_actor2.data, response.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        movie.genres.add(Genre.objects.create(name="Action"))
        movie.actors.add(Actor.objects.create(first_name="John", last_name="Doe"))

        url = detail_url(movie.id)

        response = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "TEST MOVIE",
            "description": "TEST DESC",
            "duration": 76,
        }

        response = self.client.post(MOVIE_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieViewSetTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@mail.com",
            password="testpassword",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        payload = {
            "title": "TEST MOVIE",
            "description": "TEST DESC",
            "duration": 76,
        }

        response = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(id=response.data["id"])

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_create_movie_with_genres_and_actors(self):
        genre = Genre.objects.create(name="Action")
        genre2 = Genre.objects.create(name="Story")

        actor = Actor.objects.create(first_name="John", last_name="Doe")
        actor2 = Actor.objects.create(first_name="Jane", last_name="Doe")

        payload = {
            "title": "TEST MOVIE",
            "description": "TEST DESC",
            "duration": 76,
            "genres": [genre.id, genre2.id],
            "actors": [actor.id, actor2.id],
        }

        response = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(id=response.data["id"])
        genres = movie.genres.all()
        actors = movie.actors.all()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn(genre, genres)
        self.assertIn(genre2, genres)
        self.assertIn(actor, actors)
        self.assertIn(actor2, actors)
        self.assertEqual(genres.count(), 2)
        self.assertEqual(actors.count(), 2)

    def test_delete_movie_not_allowed(self):
        movie = sample_movie()

        url = detail_url(movie.id)

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
