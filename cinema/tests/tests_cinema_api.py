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


def sample_movie(**kwargs) -> Movie:
    defaults = {
        "title": "test_1",
        "description": "something about test_1",
        "duration": 123,
    }
    defaults.update(kwargs)
    return Movie.objects.create(**defaults)


class UnauthenticatedCinemaApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_required_auth(self):
        response = self.client.get(MOVIE_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedCinemaApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@mail.test",
            password="testpassword"
        )
        self.client.force_authenticate(self.user)

        self.genres_1 = Genre.objects.create(name="Action")
        self.genres_2 = Genre.objects.create(name="Drama")

        self.actors_1 = Actor.objects.create(first_name="Bob", last_name="Bobov")
        self.actors_2 = Actor.objects.create(first_name="Ivan", last_name="Savage")
        self.actors_3 = Actor.objects.create(first_name="Evgenii", last_name="But")

        self.movie_1 = sample_movie(id=1, title="inception")
        self.movie_1.genres.set([self.genres_1, self.genres_2])
        self.movie_1.actors.set([self.actors_1, self.actors_2])

        self.movie_2 = sample_movie(id=2, title="war on ships")
        self.movie_2.genres.set([self.genres_2])
        self.movie_2.actors.set([self.actors_1, self.actors_3])

    def test_movie_list(self):
        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_movie_filter_by_title(self):
        res = self.client.get(MOVIE_URL, {"title": f"{self.movie_1.title}"})
        filtered_movies = Movie.objects.filter(title=self.movie_1.title)
        serializer = MovieListSerializer(filtered_movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_movie_filter_by_genres(self):
        res = self.client.get(MOVIE_URL, {"genres": [self.genres_2.id]})
        filtered_movies = Movie.objects.filter(genres__in=[self.genres_2.id])
        serializer = MovieListSerializer(filtered_movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_movie_filter_by_actors(self):
        res = self.client.get(MOVIE_URL, {"actors": [self.actors_2.id]})

        movie_with_needed_actor = MovieListSerializer(self.movie_1)
        movie_without_needed_actor = MovieListSerializer(self.movie_2)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(movie_with_needed_actor.data, res.data)
        self.assertNotIn(movie_without_needed_actor.data, res.data)

    def test_retrieve_movie_detail(self):
        url = detail_url(self.movie_2.id)
        res = self.client.get(url)

        serializer = MovieDetailSerializer(self.movie_2)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_is_forbidden(self):
        payload = {
            "title": "Test title",
            "description": "Test description",
            "duration": 87,
            "genres": [self.genres_2.id, self.genres_1.id],
            "actors": [self.actors_1.id, self.actors_2.id]
        }
        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminCinemaApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@test.com",
            password="admin.test",
            is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        genres_1 = Genre.objects.create(name="Action")

        actors_1 = Actor.objects.create(first_name="Bob", last_name="Bobov")
        actors_2 = Actor.objects.create(first_name="Ivan", last_name="Savage")
        payload = {
            "title": "Test title",
            "description": "Test description",
            "duration": 87,
            "genres": [genres_1.id],
            "actors": [actors_1.id, actors_2.id]
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        movie = Movie.objects.get(id=res.data["id"])

        self.assertEqual(movie.title, payload['title'])
        self.assertEqual(movie.description, payload['description'])
        self.assertEqual(movie.duration, payload['duration'])

        genres_ids = movie.genres.values_list('id', flat=True)
        actors_ids = movie.actors.values_list('id', flat=True)

        self.assertEqual(list(genres_ids), payload['genres'])
        self.assertEqual(list(actors_ids), payload['actors'])
