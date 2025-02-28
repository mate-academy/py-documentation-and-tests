from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


def sample_movie(**params):
    defaults = {
        "title": "Sample movie",
        "description": "Sample description",
        "duration": 90,
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)


def sample_genre(**params):
    defaults = {"name": "Drama"}
    defaults.update(params)
    return Genre.objects.create(**defaults)


def sample_actor(**params):
    defaults = {"first_name": "George", "last_name": "Clooney"}
    defaults.update(params)
    return Actor.objects.create(**defaults)


class MovieViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)
        self.movie = sample_movie()
        self.genre = sample_genre()
        self.actor = sample_actor()
        self.movie.genres.add(self.genre)
        self.movie.actors.add(self.actor)

    def test_list_movies(self):
        response = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_filter_movies_by_title(self):
        movie1 = sample_movie(title="Inception")
        movie2 = sample_movie(title="Interstellar")
        response = self.client.get(MOVIE_URL, {"title": "Inception"})
        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        self.assertIn(serializer1.data, response.data)
        self.assertNotIn(serializer2.data, response.data)

    def test_filter_movies_by_genre(self):
        another_genre = sample_genre(name="Action")
        another_movie = sample_movie(title="Mad Max")
        another_movie.genres.add(another_genre)
        response = self.client.get(MOVIE_URL, {"genres": self.genre.id})
        serializer1 = MovieListSerializer(self.movie)
        serializer2 = MovieListSerializer(another_movie)
        self.assertIn(serializer1.data, response.data)
        self.assertNotIn(serializer2.data, response.data)

    def test_retrieve_movie_detail(self):
        url = detail_url(self.movie.id)
        response = self.client.get(url)
        serializer = MovieDetailSerializer(self.movie)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_create_movie(self):
        payload = {
            "title": "New Movie",
            "description": "A new movie description",
            "duration": 120,
            "genres": [self.genre.id],
            "actors": [self.actor.id],
        }
        response = self.client.post(MOVIE_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(title=payload["title"])
        self.assertEqual(movie.description, payload["description"])
