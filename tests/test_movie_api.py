from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")

MOVIE_SESSION_URL = reverse("cinema:moviesession-list")


def detail_url(movie_id: int):
    return reverse("cinema:movie-detail", args=[movie_id])


def sample_movie(**params):
    defaults = {
        "title": "Sample movie",
        "description": "Sample description",
        "duration": 100,
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
    defaults = {
        "first_name": "Keanu",
        "last_name": "Reeves"
    }
    defaults.update(params)
    return Actor.objects.create(**defaults)


class UnauthenticatedMovieApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="12345@test.com",
            password="12345test"
        )
        self.client.force_authenticate(self.user)

    def test_list_movie(self):
        sample_movie()
        movie_with_actor = sample_movie()
        movie_with_genre = sample_movie()

        actor1 = sample_actor()
        actor2 = sample_actor(first_name="Will", last_name="Smith")

        genre1 = sample_genre()
        genre2 = sample_genre(name="Melodrama")

        movie_with_genre.genres.add(genre1, genre2)
        movie_with_actor.actors.add(actor1, actor2)

        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_by_actors(self):
        movie_with_actors = sample_movie(
            title="Movie_with_actors",
            description="Good movie",
            duration=150
        )

        actor1 = sample_actor()
        actor2 = sample_actor(first_name="Will", last_name="Smith")
        actor3 = sample_actor(first_name="Ivan", last_name="Ivanenko")

        movie_with_actors.actors.add(actor1, actor2, actor3)

        movie_without_actors = sample_movie()

        res = self.client.get(MOVIE_URL, {"actors": f"{actor1.id}, {actor2.id}, {actor3.id}"})

        serializer1 = MovieListSerializer(movie_with_actors)
        serializer2 = MovieListSerializer(movie_without_actors)

        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

    def test_retrieve_movie_detail(self):

        movie = sample_movie()
        movie.actors.add(Actor.objects.create(first_name="Will", last_name="Smith"))

        url = detail_url(movie.id)
        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):

        payload = {
            "title": "Movie_with_actors",
            "description": "Good movie",
            "duration": 150
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@test.com",
            password="12345test",
            is_staff=True
        )
        self.client.force_authenticate(self.user)

    def tes_create_movie(self):
        payload = {
            "title": "Movie_with_actors",
            "description": "Good movie",
            "duration": 150
        }
        res = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=res.data["id"])
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_create_movie_with_genres_and_actors(self):
        genre1 = sample_genre()
        genre2 = sample_genre(name="Melodrama")

        actor1 = sample_actor()
        actor2 = sample_actor(first_name="Will", last_name="Smith")

        payload = {
            "title": "Movie",
            "description": "Good movie",
            "duration": 150,
            "genres": [genre1.id, genre2.id],
            "actors": [actor1.id, actor2.id],
        }

        res = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(id=res.data["id"])
        genres = movie.genres.all()
        actors = movie.actors.all()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(genres.count(), 2)
        self.assertEqual(actors.count(), 2)
        self.assertIn(genre1, genres)
        self.assertIn(genre2, genres)
        self.assertIn(actor1, actors)
        self.assertIn(actor2, actors)

    def test_deleted_movie_not_allowed(self):
        movie = sample_movie()
        url = detail_url(movie.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

