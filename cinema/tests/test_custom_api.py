from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from cinema.models import Movie, Actor, Genre
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")

def sample_movie(**params) -> Movie:
    defaults = {
        "title": "Avengers",
        "description": "The Avengers were a team of extraordinary individuals, with either superpowers or other special characteristics",
        "duration": 100,
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)

def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=(movie_id,))

class UnAuthenticateTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.test",
            password="testtest"
        )
        self.client.force_authenticate(self.user)
        self.actor_1 = Actor.objects.create(first_name="Robert", last_name="Downey Jr.")
        self.actor_2 = Actor.objects.create(first_name="Chris", last_name="Evans")

    def test_movie_list(self):
        sample_movie()
        movie_with_actors = sample_movie()
        movie_with_actors.actors.add(self.actor_1)
        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_movie_filter(self):
        movie_without_actors = sample_movie()
        movie_with_actor_1 = sample_movie(title="TestMovie2")
        movie_with_actor_2 = sample_movie(title="TestMovie3")

        movie_with_actor_1.actors.add(self.actor_1)
        movie_with_actor_2.actors.add(self.actor_2)

        res = self.client.get(
            MOVIE_URL,
            {"actors": f"{self.actor_1.id},{self.actor_2.id}"}
        )

        serializer_without_actors = MovieListSerializer(movie_without_actors)
        serializer_movie_with_actor_1 = MovieListSerializer(movie_with_actor_1)
        serializer_movie_with_actor_2 = MovieListSerializer(movie_with_actor_2)

        self.assertIn(serializer_movie_with_actor_1.data, res.data)
        self.assertIn(serializer_movie_with_actor_2.data, res.data)
        self.assertNotIn(serializer_without_actors.data, res.data)

    def test_retreieve_movie_detail(self):
        movie = sample_movie()
        movie.actors.add(self.actor_1)

        url = detail_url(movie.id)
        res = self.client.get(url)
        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "TestMovie",
            "description": "A test movie",
            "duration": 100,
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@test.test",
            password="testtest",
            is_staff=True
        )
        self.client.force_authenticate(self.user)
        self.actor_1 = Actor.objects.create(first_name="Robert", last_name="Downey Jr.")
        self.actor_2 = Actor.objects.create(first_name="Chris", last_name="Evans")

    def test_create_movie(self):
        payload = {
            "title": "TestMovie",
            "description": "A test movie",
            "duration": 100,
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(id=res.data['id'])

        for key, value in payload.items():
            self.assertEqual(payload[key], getattr(movie, key))

    def test_create_movie_with_actors(self):
        payload = {
            "title": "TestMovie",
            "description": "A test movie",
            "duration": 100,
            "actors": [self.actor_1.id, self.actor_2.id]
        }

        res = self.client.post(MOVIE_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        movie = Movie.objects.get(id=res.data["id"])
        actors = movie.actors.all()

        self.assertIn(self.actor_1, actors)
        self.assertIn(self.actor_2, actors)
        self.assertEqual(actors.count(), 2)

    def test_delete_movie_not_allowed(self):
        movie = sample_movie()

        url = detail_url(movie.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
