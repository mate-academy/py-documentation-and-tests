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
        "title": "TestMovie",
        "description": "some description",
        "duration": 120
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)

def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=(movie_id,))


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
            email="test@email.com", password="testpass"
        )
        self.client.force_authenticate(self.user)

    def test_movie_list(self):
        sample_movie()
        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.data, serializer.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_filter_movies_by_actors(self):
        movie_without_actors = sample_movie()
        movie_with_actor_1 = sample_movie(title="testmovie1")
        movie_with_actor_2 = sample_movie(title="testmovie2")

        actor_1 = Actor.objects.create(first_name="Actor", last_name="1")
        actor_2 = Actor.objects.create(first_name="Actor", last_name="2")

        movie_with_actor_1.actors.add(actor_1)
        movie_with_actor_2.actors.add(actor_2)

        res = self.client.get(
            MOVIE_URL,
            {"actors": f"{actor_1.id},{actor_2.id}"}
        )

        serializer_without_actors = MovieListSerializer(movie_without_actors)
        serializer_movie_with_actor_1 = MovieListSerializer(movie_with_actor_1)
        serializer_movie_with_actor_2 = MovieListSerializer(movie_with_actor_2)

        self.assertIn(serializer_movie_with_actor_1.data, res.data)
        self.assertIn(serializer_movie_with_actor_2.data, res.data)
        self.assertNotIn(serializer_without_actors.data, res.data)

    def test_filter_movies_by_genres(self):
        movie_without_genres = sample_movie()
        movie_with_genre_1 = sample_movie(title="testmovie1")
        movie_with_genre_2 = sample_movie(title="testmovie2")

        genre_1 = Genre.objects.create(name="genre1")
        genre_2 = Genre.objects.create(name="genre2")

        movie_with_genre_1.genres.add(genre_1)
        movie_with_genre_2.genres.add(genre_2)

        res = self.client.get(
            MOVIE_URL,
            {"genres": f"{genre_1.id},{genre_2.id}"}
        )

        serializer_without_genres = MovieListSerializer(movie_without_genres)
        serializer_movie_with_genre_1 = MovieListSerializer(movie_with_genre_1)
        serializer_movie_with_genre_2 = MovieListSerializer(movie_with_genre_2)

        self.assertIn(serializer_movie_with_genre_1.data, res.data)
        self.assertIn(serializer_movie_with_genre_2.data, res.data)
        self.assertNotIn(serializer_without_genres.data, res.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        movie.actors.add(Actor.objects.create(first_name="Actor", last_name="1"))

        url = detail_url(movie.id)

        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "TestMovie",
            "description": "description",
            "duration": 100,
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

class AdminMovieTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@email.com",
            password="testpass",
            is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        payload = {
            "title": "TestMovie",
            "description": "description",
            "duration": 100,
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        movie = Movie.objects.get(id=res.data["id"])

        for key, value in payload.items():
            self.assertEqual(payload[key], getattr(movie, key))

    def test_create_movie_with_actors(self):
        actor_1 = Actor.objects.create(first_name="Actor", last_name="1")
        actor_2 = Actor.objects.create(first_name="Actor", last_name="2")
        payload = {
            "title": "TestMovie",
            "description": "description",
            "duration": 100,
            "actors": [actor_1.id, actor_2.id]
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        movie = Movie.objects.get(id=res.data["id"])
        actors = movie.actors.all()
        self.assertIn(actor_1, actors)
        self.assertIn(actor_2, actors)
        self.assertEqual(actors.count(), 2)
