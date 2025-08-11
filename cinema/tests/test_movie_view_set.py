from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework.reverse import reverse

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieSerializer, MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


def sample_movie(**params) -> Movie:
    defaults = {
        "title": "The Great Brick",
        "description": "The Great Brick is the film about something great",
        "duration": 60,
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)


def sample_actor(**params) -> Actor:
    defaults = {
        "first_name": "John",
        "last_name": "Doe",
    }
    defaults.update(params)
    return Actor.objects.create(**defaults)


def sample_genre(**params) -> Genre:
    defaults = {
        "name": "Action"
    }
    defaults.update(params)
    return Genre.objects.create(**defaults)


class UnauthenticatedUserTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedUserTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com",
            password="testpassword",
        )
        self.client.force_authenticate(self.user)

    def test_movie_list(self):
        actor = sample_actor()
        genre = sample_genre()
        movie = sample_movie()
        movie.genres.add(genre)
        movie.actors.add(actor)

        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_actor(self):
        actor1 = sample_actor(first_name="John", last_name="Doe")
        actor2 = sample_actor(first_name="Jane", last_name="Smith")
        movie = sample_movie()
        movie1 = sample_movie(title="Movie One")
        movie2 = sample_movie(title="Movie Two")
        movie1.actors.add(actor1)
        movie2.actors.add(actor2)

        res = self.client.get(MOVIE_URL, {"actors": f"{actor1.id},{actor2.id}"})

        serializer = MovieSerializer(movie)
        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)

        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer.data, res.data)

    def test_filter_movies_by_genre(self):
        genre1 = sample_genre(name="Action")
        genre2 = sample_genre(name="Sci-Fi")
        movie = sample_movie()
        movie1 = sample_movie(title="Movie One")
        movie2 = sample_movie(title="Movie Two")
        movie1.genres.add(genre1)
        movie2.genres.add(genre2)

        res = self.client.get(MOVIE_URL, {"genres": f"{genre1.id},{genre2.id}"})

        serializer = MovieSerializer(movie)
        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)

        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer.data, res.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        movie.genres.add(sample_genre())
        movie.actors.add(sample_actor())

        url = detail_url(movie.id)

        res = self.client.get(url)
        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "The NEW Great Brick",
            "description": "The NEW Great Brick is the film about something great and new",
            "duration": 67,
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@test.com",
            password="adminpassword",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        payload = {
            "title": "The NEW Great Brick",
            "description": "The NEW Great Brick is the film about something great and new",
            "duration": 67,
        }

        res = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_create_movie_with_actors(self):
        actor1 = sample_actor(first_name="John", last_name="Doe")
        actor2 = sample_actor(first_name="Jane", last_name="Smith")
        payload = {
            "title": "The NEW Great Brick",
            "description": "The NEW Great Brick is the film about something great and new",
            "duration": 67,
            "actors": [actor1.id, actor2.id]
        }

        res = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(id=res.data["id"])
        actors = movie.actors.all()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn(actor1, actors)
        self.assertIn(actor2, actors)
        self.assertEqual(actors.count(), 2)

    def test_create_movie_with_genres(self):
        genre1 = sample_genre(name="Action")
        genre2 = sample_genre(name="Sci-Fi")
        payload = {
            "title": "The NEW Great Brick",
            "description": "The NEW Great Brick is the film about something great and new",
            "duration": 67,
            "genres": [genre1.id, genre2.id]
        }

        res = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(id=res.data["id"])
        genres = movie.genres.all()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn(genre1, genres)
        self.assertIn(genre2, genres)
        self.assertEqual(genres.count(), 2)




