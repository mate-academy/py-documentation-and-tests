from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient
from django.test import TestCase

from cinema.models import Movie, Actor, Genre
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


def sample_movie(**params) -> Movie:
    genre, _ = Genre.objects.get_or_create(name="Default Test Genre")
    actor_1, _ = Actor.objects.get_or_create(first_name="Test", last_name="Testing")

    defaults = {
        "title": "Movie Title",
        "duration": 50,
        "description": "Movie Description",
    }

    defaults.update(params)

    movie = Movie.objects.create(**defaults)

    movie.actors.add(actor_1)
    movie.genres.add(genre)

    return movie


class UnauthenticatedMovieApiTets(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(MOVIE_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTets(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com",
            password="testpassword",
        )
        self.client.force_authenticate(self.user)

    def test_get_movie_list(self):
        sample_movie(title="Movie 1")
        sample_movie(title="Movie 2")
        response = self.client.get(MOVIE_URL)

        items = Movie.objects.all().order_by("id")  # get a list of data from db
        serializer = MovieListSerializer(items, many=True)

        self.assertEqual(serializer.data, response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_movie_detail(self) -> None:
        movie = sample_movie()
        url = detail_url(movie.id)
        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(serializer.data, res.data)

    def test_filter_movies_by_actors(self):
        movie_without_test_actor = sample_movie()
        movie_with_test_actor = sample_movie(title="Terminator")

        actor = Actor.objects.create(first_name="Arnold", last_name="Schwarzenegger")
        movie_with_test_actor.actors.add(actor)

        res = self.client.get(MOVIE_URL, {"actors": f"{actor.id}"})

        serializer_without_test_actor = MovieListSerializer(movie_without_test_actor)
        serializer_with_arnold = MovieListSerializer(movie_with_test_actor)

        self.assertIn(serializer_with_arnold.data, res.data)
        self.assertNotIn(serializer_without_test_actor.data, res.data)

    def test_filter_movies_by_genres(self):
        movie_without_test_genre = sample_movie()
        movie_with_test_genre = sample_movie(title="Harry Potter")

        genre = Genre.objects.create(name="Adventure")
        movie_with_test_genre.genres.add(genre)

        res = self.client.get(MOVIE_URL, {"genres": genre.id})

        serializer_without_test_genre = MovieListSerializer(movie_without_test_genre)
        serializer_with_adventure = MovieListSerializer(movie_with_test_genre)

        self.assertIn(serializer_with_adventure.data, res.data)
        self.assertNotIn(serializer_without_test_genre.data, res.data)

    def test_filter_movies_by_title(self):
        movie_with_invalid_name = sample_movie(title="Invalid")
        movie_with_true_name = sample_movie(title="Mad Max")

        res = self.client.get(MOVIE_URL, {"title": "Mad"})

        serializer_with_invalid_name = MovieListSerializer(movie_with_invalid_name)
        serializer_with_true_name = MovieListSerializer(movie_with_true_name)

        self.assertIn(serializer_with_true_name.data, res.data)
        self.assertNotIn(serializer_with_invalid_name.data, res.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Movie Title",
            "duration": 50,
            "description": "Movie Description",
        }

        response = self.client.post(MOVIE_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@admin.com",
            password="adminpassword",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        actor = Actor.objects.create(first_name="John", last_name="Doe")
        genre = Genre.objects.create(name="Drama")
        payload = {
            "title": "Admin Movie Title",
            "description": "Admin Movie Description",
            "duration": 55,
            "actors": [actor.id],
            "genres": [genre.id],
        }
        response = self.client.post(MOVIE_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        exists = Movie.objects.filter(title=payload["title"]).exists()
        self.assertTrue(exists)
