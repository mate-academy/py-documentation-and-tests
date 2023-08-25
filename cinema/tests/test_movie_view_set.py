from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import Movie, Actor, Genre
from cinema.serializers import MovieListSerializer, MovieDetailSerializer, MovieSerializer

MOVIE_URL = reverse("cinema:movie-list")


def detail_url(movie_id: int):
    return reverse("cinema:movie-detail", args=[movie_id])


def sample_movie(**params):
    defaults = {
        "title": "Test movie",
        "description": "Test description",
        "duration": 120,
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
    defaults = {"first_name": "George", "last_name": "Clooney"}
    defaults.update(params)

    return Actor.objects.create(**defaults)


class UnauthentikatedMovieTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticateMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "cinephile@cinema.com", "password"
        )
        self.client.force_authenticate(self.user)

    def test_movie_list(self):
        sample_movie()
        movie_with_actors = sample_movie()

        movie_with_actors.actors.add(sample_actor())

        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_with_actors(self):
        movie1 = sample_movie(title="test title 1")
        movie2 = sample_movie(title="test title 2")
        movie3 = sample_movie(title="test title 3")

        actor1 = sample_actor(first_name="first name 1", last_name="last name 1")
        actor2 = sample_actor(first_name="first name 2", last_name="last name 2")
        actor3 = sample_actor(first_name="first name 3", last_name="last name 3")

        movie1.actors.add(actor3, actor1)
        movie2.actors.add(actor2)

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie3)

        res = self.client.get(MOVIE_URL, {"actors": f"{actor1.id},{actor2.id},{actor3.id}"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_filter_by_title(self):
        movie1 = sample_movie(title="test title 1")
        movie2 = sample_movie(title="test title 2")
        movie3 = sample_movie(title="test title 3")

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie3)

        res = self.client.get(MOVIE_URL, {"title": f"{movie2.title}"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertNotIn(serializer3.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer1.data, res.data)

    def test_filter_by_genres(self):
        movie1 = sample_movie(title="test title 1")
        movie2 = sample_movie(title="test title 2")
        movie3 = sample_movie(title="test title 3")

        genre1 = sample_genre(name="genre 1")
        genre2 = sample_genre(name="genre 2")
        genre3 = sample_genre(name="genre 3")

        movie1.genres.add(genre1, genre2)
        movie2.genres.add(genre3, genre2)
        movie3.genres.add(genre1, genre3)

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie3)

        res = self.client.get(MOVIE_URL, {"genres": f"{genre2.id}"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_retrieve_movie_details(self):
        movie = sample_movie()
        # actor = sample_actor()
        # movie.actors.add(actor)
        serializers = MovieDetailSerializer(movie)
        url = detail_url(movie.id)
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(serializers.data, res.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "test movie",
            "description": "test description",
            "duration": 120,
        }
        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "cinephile@cinema.com",
            "password",
            is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        genre = sample_genre()
        actor = sample_actor()
        payload = {
            "title": "test movie",
            "description": "test description",
            "duration": 120,
            "genres": [genre.id],
            "actors": [actor.id]
        }
        res = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=res.data["id"])
        serializer = MovieSerializer(movie)

        for key in payload.keys():
            self.assertEqual(payload[key], serializer.data[key])
