from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


def sample_genre(name="Action"):
    return Genre.objects.create(name=name)


def sample_actor(first_name="Tom", last_name="Cruise"):
    return Actor.objects.create(first_name=first_name, last_name=last_name)


def sample_movie(genres=None, actors=None, **params):
    defaults = {
        "title": "Top Gun",
        "description": "A classic pilot movie",
        "duration": 120,
    }
    defaults.update(params)
    movie = Movie.objects.create(**defaults)

    if genres:
        movie.genres.set(genres)
    if actors:
        movie.actors.set(actors)

    return movie


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
            "user@test.com", "testpass"
        )
        self.client.force_authenticate(self.user)

    def test_retrieve_movies(self):
        sample_movie()
        sample_movie(title="Avatar")

        res = self.client.get(MOVIE_URL)

        movies = Movie.objects.all().order_by("title")
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"], serializer.data)


    def test_filter_movies_by_title(self):
        movie1 = sample_movie(title="Titanic")
        movie2 = sample_movie(title="Shrek")

        res = self.client.get(MOVIE_URL, {"title": "titanic"})

        self.assertIn(MovieListSerializer(movie1).data, res.data["results"])
        self.assertNotIn(MovieListSerializer(movie2).data, res.data["results"])

    def test_filter_movies_by_genre(self):
        genre1 = sample_genre(name="Sci-Fi")
        genre2 = sample_genre(name="Drama")
        movie1 = sample_movie(title="Interstellar", genres=[genre1])
        movie2 = sample_movie(title="Notebook", genres=[genre2])

        res = self.client.get(MOVIE_URL, {"genres": f"{genre1.id}"})

        self.assertIn(MovieListSerializer(movie1).data, res.data["results"])
        self.assertNotIn(MovieListSerializer(movie2).data, res.data["results"])

    def test_filter_movies_by_actor(self):
        actor1 = sample_actor("Brad", "Pitt")
        actor2 = sample_actor("Will", "Smith")

        movie1 = sample_movie(title="Fight Club", actors=[actor1])
        movie2 = sample_movie(title="Men in Black", actors=[actor2])

        res = self.client.get(MOVIE_URL, {"actors": f"{actor1.id}"})

        self.assertIn(MovieListSerializer(movie1).data, res.data["results"])
        self.assertNotIn(MovieListSerializer(movie2).data, res.data["results"])

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Inception",
            "description": "Dream heist",
            "duration": 148,
        }
        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_user = get_user_model().objects.create_superuser(
            "admin@test.com", "adminpass"
        )
        self.client.force_authenticate(self.admin_user)

    def test_create_movie(self):
        genre = sample_genre()
        actor = sample_actor()
        payload = {
            "title": "The Matrix",
            "description": "Neo discovers the truth",
            "duration": 136,
            "genres": [genre.id],
            "actors": [actor.id],
        }
        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(id=res.data["id"])
        self.assertEqual(movie.title, payload["title"])
        self.assertEqual(movie.description, payload["description"])
        self.assertEqual(movie.duration, payload["duration"])
        self.assertIn(genre, movie.genres.all())
        self.assertIn(actor, movie.actors.all())

    def test_retrieve_movie_detail(self):
        genre = sample_genre()
        actor = sample_actor()
        movie = sample_movie(genres=[genre], actors=[actor])

        url = detail_url(movie.id)
        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)
