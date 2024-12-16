from django.contrib.auth import get_user_model
from django.template.context_processors import request
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework.reverse import reverse

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")

class UnauthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(MOVIE_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


def sample_movie(**params) -> Movie:
    defaults = {
        "title": "Sample movie",
        "description": "Sample description",
        "duration": 90,
    }

    defaults.update(params)

    return Movie.objects.create(**defaults)


def sample_genre(**params) -> Genre:
    defaults = {
        "name": "Drama",
    }
    defaults.update(params)

    return Genre.objects.create(**defaults)


def sample_actor(**params) -> Actor:
    defaults = {"first_name": "George", "last_name": "Clooney"}
    defaults.update(params)

    return Actor.objects.create(**defaults)


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user@example.com",
            password="testpassword",
        )

        self.client.force_authenticate(self.user)

    def test_movies_list(self):
        actor_one = sample_actor()
        actor_two = sample_actor(first_name="test_first", last_name="test_last")

        genre_one = sample_genre()
        genre_two = sample_genre(name="Comedy")

        movie = sample_movie()

        movie.actors.add(actor_one, actor_two)
        movie.genres.add(genre_one, genre_two)

        response = self.client.get(MOVIE_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_filter_movies_by_actor(self):
        actor_one = sample_actor(
            first_name="test_first", last_name="test_last"
        )
        actor_two = sample_actor(
            first_name="test_second", last_name="test_second"
        )

        movie = sample_movie()
        movie_one = sample_movie(
            title="first", description="second test description", duration=70
        )
        movie_two = sample_movie(
            title="test", description="test description", duration=60
        )

        movie_one.actors.add(actor_one)
        movie_two.actors.add(actor_two)

        response_filter_title = self.client.get(
            MOVIE_URL, {"actors": f"{actor_one.id},{actor_two.id}"}
        )

        serializer = MovieListSerializer(movie)
        serializer_with_actor_one = MovieListSerializer(movie_one)
        serializer_with_actor_two = MovieListSerializer(movie_two)

        self.assertIn(serializer_with_actor_one.data, response_filter_title.data)
        self.assertIn(serializer_with_actor_two.data, response_filter_title.data)
        self.assertNotIn(serializer.data, response_filter_title.data)

    def test_filter_movies_by_genre(self):
        genre_one = sample_genre(name="Sci-Fi")
        genre_two = sample_genre(name="Comedy")

        movie = sample_movie()
        movie_one = sample_movie(
            title="first", description="second test description", duration=70
        )
        movie_two = sample_movie(
            title="test", description="test description", duration=60
        )

        movie_one.genres.add(genre_one)
        movie_two.genres.add(genre_two)

        response_filter_title = self.client.get(
            MOVIE_URL, {"genres": f"{genre_one.id},{genre_two.id}"}
        )

        serializer = MovieListSerializer(movie)
        serializer_with_genre_one = MovieListSerializer(movie_one)
        serializer_with_genre_two = MovieListSerializer(movie_two)

        self.assertIn(serializer_with_genre_one.data, response_filter_title.data)
        self.assertIn(serializer_with_genre_two.data, response_filter_title.data)
        self.assertNotIn(serializer.data, response_filter_title.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        movie.genres.add(Genre.objects.create(name="Sci-Fi"))

        url = reverse("cinema:movie-detail", args=(movie.id,))

        response = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Sample movie",
            "description": "Sample description",
            "duration": 90,
        }

        response = self.client.post(MOVIE_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user@example.com",
            password="testpassword",
            is_staff=True,
        )

        self.client.force_authenticate(self.user)

    def test_create_movie_with_genres_actors(self):
        sample_actor()
        sample_genre()

        actor = Actor.objects.get(id=1)
        genre = Genre.objects.get(id=1)

        payload = {
            "title": "Sample movie",
            "description": "Sample description",
            "duration": 90,
            "genres": actor.id,
            "actors": genre.id,
        }

        response = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(id=response.data["id"])
        movie_actor = movie.actors.all()
        movie_genre =movie.genres.all()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertIn(actor, movie_actor)
        self.assertIn(genre, movie_genre)

        self.assertEqual(movie_actor.count(), 1)
        self.assertEqual(movie_genre.count(), 1)

    def test_delete_movie_not_allowed(self):
        movie = sample_movie()
        url = reverse("cinema:movie-detail", args=(movie.id,))
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)




