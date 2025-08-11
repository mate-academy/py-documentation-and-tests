from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")


def sample_movie(**params) -> Movie:
    defaults = {
        "title": "test_title",
        "description": "test_description",
        "duration": "100",
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)


def sample_genre(**params) -> Genre:
    defaults = {
        "name": "test_genre",
    }
    defaults.update(params)
    return Genre.objects.create(**defaults)


def sample_actor(**params) -> Actor:
    defaults = {
        "first_name": "John",
        "last_name": "Dow",
    }
    defaults.update(params)
    return Actor.objects.create(**defaults)

def detail_url(movie_id: int):
    return reverse("cinema:movie-detail", args=(movie_id,))


class UnauthenticatedMovieViewSetTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self):
        result = self.client.get(MOVIE_URL)
        self.assertEqual(result.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieViewSetTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@user.com",
            password="test_Pa55w0rD"
        )
        self.client.force_authenticate(self.user)

    def test_auth(self):
        result = self.client.get(MOVIE_URL)
        self.assertEqual(result.status_code, status.HTTP_200_OK)

    def test_movie_list(self):
        sample_movie()
        movie = sample_movie()
        actor = sample_actor()
        genre = sample_genre()

        movie.actors.add(actor)
        movie.genres.add(genre)

        result = self.client.get(MOVIE_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(result.status_code, status.HTTP_200_OK)
        self.assertEqual(result.data, serializer.data)

    def test_filter_movies_by_genres(self):
        movie_without_genres = sample_movie()
        movie_with_genre_1 = sample_movie(title="movie_1", description="test", duration=80)
        movie_with_genre_2 = sample_movie(title="movie_2", description="test2", duration=90)

        genre_1 = sample_genre(name="test_1")
        genre_2 = sample_genre(name="test_2")

        movie_with_genre_1.genres.add(genre_1)
        movie_with_genre_2.genres.add(genre_2)

        res = self.client.get(MOVIE_URL, {
            "genres": f"{genre_1.id},{genre_2.id}"
        })
        serializer_without_genres = MovieListSerializer(movie_without_genres)
        serializer_movie_genres_1 = MovieListSerializer(movie_with_genre_1)
        serializer_movie_genres_2 = MovieListSerializer(movie_with_genre_2)

        self.assertIn(serializer_movie_genres_1.data, res.data)
        self.assertIn(serializer_movie_genres_2.data, res.data)
        self.assertNotIn(serializer_without_genres, res.data)


    def test_filter_movies_by_actors(self):
        movie_without_actors = sample_movie()
        movie_with_actors_1 = sample_movie(title="movie_1")
        movie_with_actors_2 = sample_movie(title="movie_2")

        actor = sample_actor(first_name="John", last_name="Black")
        actress = sample_actor(first_name="Jane", last_name="White")

        movie_with_actors_1.actors.add(actor)
        movie_with_actors_2.actors.add(actress)

        res = self.client.get(MOVIE_URL, {
            "actors": f"{actor.id},{actress.id}"
        })
        serializer_without_actors = MovieListSerializer(movie_without_actors)
        serializer_movie_actors_1 = MovieListSerializer(movie_with_actors_1)
        serializer_movie_actors_2 = MovieListSerializer(movie_with_actors_2)

        self.assertIn(serializer_movie_actors_1.data, res.data)
        self.assertIn(serializer_movie_actors_2.data, res.data)
        self.assertNotIn(serializer_without_actors, res.data)


    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        movie.genres.add(sample_genre())
        movie.actors.add(sample_actor())

        url = detail_url(movie_id=movie.id)
        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "test_movie",
            "description": "test_description",
            "duration": 90,
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieList(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@admin.com",
            password="test_Pa55w0rD",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        payload = {
            "title": "test_admin_movie",
            "description": "test_description",
            "duration": 80,
        }

        res = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_create_movie_with_genres(self):
        genre_1 = sample_genre(name="test_1")
        genre_2 = sample_genre(name="test_2")

        payload = {
            "title": "test_admin_movie",
            "description": "test_description",
            "duration": 80,
            "genres": [genre_1.id, genre_2.id]
        }

        res = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(id=res.data["id"])

        genres = movie.genres.all()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn(genre_1, genres)
        self.assertIn(genre_2, genres)
        self.assertEqual(genres.count(), 2)


    def test_create_movie_with_actors(self):
        actor = sample_actor(first_name="John", last_name="Black")
        actress = sample_actor(first_name="Jane", last_name="White")

        payload = {
            "title": "test_admin_movie",
            "description": "test_description",
            "duration": 80,
            "actors": [actor.id, actress.id]
        }

        res = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(id=res.data["id"])

        actors = movie.actors.all()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn(actor, actors)
        self.assertIn(actress, actors)
        self.assertEqual(actors.count(), 2)

    def test_delete_not_allowed(self):
        movie = sample_movie()
        url = detail_url(movie_id=movie.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
