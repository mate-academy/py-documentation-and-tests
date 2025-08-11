from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")

def detail_url(movie_id):
    """Return movie detail URL"""
    return reverse("cinema:movie-detail", args=[movie_id])

def sample_movie(**params):
    """Create and return a sample movie"""
    defaults = {
        "title": "Sample movie",
        "description": "Sample description",
        "duration": 90,
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)

def sample_genre(**params):
    """Create and return a sample genre"""
    defaults = {"name": "Drama"}
    defaults.update(params)
    return Genre.objects.create(**defaults)

def sample_actor(**params):
    """Create and return a sample actor"""
    defaults = {"first_name": "George", "last_name": "Clooney"}
    defaults.update(params)
    return Actor.objects.create(**defaults)


class MovieViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user("test@example.com", "testpass")
        self.client.force_authenticate(self.user)

    def test_list_movies(self):
        """Test retrieving a list of movies"""
        movie1 = sample_movie(title="Action Movie")
        movie2 = sample_movie(title="Comedy Film")
        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all().order_by("id")
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_retrieve_movie(self):
        """Test retrieving a movie detail"""
        movie = sample_movie(title="Detailed Movie")
        url = detail_url(movie.id)
        res = self.client.get(url)
        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_title(self):
        """Test filtering movies by title"""
        movie1 = sample_movie(title="Action Thriller")
        movie2 = sample_movie(title="Romantic Comedy")
        movie3 = sample_movie(title="Action Drama")
        res = self.client.get(MOVIE_URL, {"title": "Action"})

        movies = Movie.objects.filter(title__icontains="Action").order_by("id")
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)
        self.assertCountEqual(res.data, serializer.data)

    def test_filter_movies_by_genres(self):
        """Test filtering movies by genres"""
        genre_drama = sample_genre(name="Drama")
        genre_action = sample_genre(name="Action")
        movie1 = sample_movie(title="Movie One")
        movie2 = sample_movie(title="Movie Two")
        movie1.genres.add(genre_drama)
        movie2.genres.add(genre_action)

        res = self.client.get(MOVIE_URL, {"genres": f"{genre_drama.id}"})
        movies = Movie.objects.filter(genres__id__in=[genre_drama.id]).distinct().order_by("id")
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_actors(self):
        """Test filtering movies by actors"""
        actor1 = sample_actor(first_name="Brad", last_name="Pitt")
        actor2 = sample_actor(first_name="Leonardo", last_name="DiCaprio")
        movie1 = sample_movie(title="Movie One")
        movie2 = sample_movie(title="Movie Two")
        movie1.actors.add(actor1)
        movie2.actors.add(actor2)

        res = self.client.get(MOVIE_URL, {"actors": f"{actor1.id}"})
        movies = Movie.objects.filter(actors__id__in=[actor1.id]).distinct().order_by("id")
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data, serializer.data)

    def test_invalid_movie_retrieve_returns_404(self):
        """Test retrieving a movie that does not exist returns 404"""
        url = detail_url(9999)
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
