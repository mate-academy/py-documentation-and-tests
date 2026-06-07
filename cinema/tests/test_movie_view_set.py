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


def sample_movie(**params):
    defaults = {
        "title": "Sample Movie",
        "description": "Sample description",
        "duration": 120,
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)


class UnauthenticatedMovieApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_auth_not_required_for_list(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_auth_not_required_for_detail(self):
        movie = sample_movie()
        res = self.client.get(detail_url(movie.id))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_auth_required_for_create(self):
        payload = {
            "title": "Inception",
            "description": "Dream within a dream",
            "duration": 148,
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user@test.com", password="password123"
        )
        self.client.force_authenticate(self.user)

    def test_list_movies(self):
        sample_movie(title="Movie 1")
        sample_movie(title="Movie 2")

        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_title(self):
        movie1 = sample_movie(title="Batman")
        movie2 = sample_movie(title="Superman")

        res = self.client.get(MOVIE_URL, {"title": "bat"})

        self.assertIn(MovieListSerializer(movie1).data, res.data)
        self.assertNotIn(MovieListSerializer(movie2).data, res.data)

    def test_filter_movies_by_genres(self):
        genre1 = Genre.objects.create(name="Action")
        genre2 = Genre.objects.create(name="Comedy")
        movie1 = sample_movie(title="Action Movie")
        movie2 = sample_movie(title="Comedy Movie")
        movie1.genres.add(genre1)
        movie2.genres.add(genre2)

        res = self.client.get(MOVIE_URL, {"genres": f"{genre1.id}"})

        self.assertIn(MovieListSerializer(movie1).data, res.data)
        self.assertNotIn(MovieListSerializer(movie2).data, res.data)

    def test_filter_movies_by_actors(self):
        actor1 = Actor.objects.create(first_name="Keanu", last_name="Reeves")
        actor2 = Actor.objects.create(first_name="Brad", last_name="Pitt")
        movie1 = sample_movie(title="Matrix")
        movie2 = sample_movie(title="Fight Club")
        movie1.actors.add(actor1)
        movie2.actors.add(actor2)

        res = self.client.get(MOVIE_URL, {"actors": f"{actor1.id}"})

        self.assertIn(MovieListSerializer(movie1).data, res.data)
        self.assertNotIn(MovieListSerializer(movie2).data, res.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        genre = Genre.objects.create(name="Sci-Fi")
        actor = Actor.objects.create(first_name="Leo", last_name="DiCaprio")
        movie.genres.add(genre)
        movie.actors.add(actor)

        res = self.client.get(detail_url(movie.id))
        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_regular_user_cannot_create_movie(self):
        payload = {
            "title": "Interstellar",
            "description": "Space travel",
            "duration": 169,
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin_user = get_user_model().objects.create_superuser(
            email="admin_viewset@test.com", password="adminpassword"
        )
        self.client.force_authenticate(self.admin_user)

    def test_create_movie(self):
        genre = Genre.objects.create(name="Drama")
        actor = Actor.objects.create(first_name="Tom", last_name="Hanks")
        payload = {
            "title": "Forrest Gump",
            "description": "Life is like a box of chocolates",
            "duration": 142,
            "genres": [genre.id],
            "actors": [actor.id],
        }

        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        movie = Movie.objects.get(id=res.data["id"])
        self.assertEqual(movie.title, payload["title"])
        self.assertEqual(movie.genres.count(), 1)
