from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")

def movie_detail_url(movie_id: int):
    return reverse("cinema:movie-detail", args=(movie_id,))


def sample_movie(**params) -> Movie:
    defaults = {
        "title": "Spider-man",
        "description": "Superhero movie",
        "duration": 130,
    }
    defaults.update(params)

    return Movie.objects.create(**defaults)


def sample_genre(**params) -> Genre:
    defaults = {
        "name": "Action",
    }
    defaults.update(params)

    return Genre.objects.create(**defaults)


def sample_actor(**params) -> Actor:
    defaults = {
        "first_name": "Tobey",
        "last_name": "Maguire",
    }
    defaults.update(params)
    return Actor.objects.create(**defaults)


class PublicTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_list_login_required(self):
        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(email="admin.user", password="Qwerty12345!")

        self.client.force_authenticate(self.user)

    def test_movie_list(self):
        sample_movie()
        movie = sample_movie()
        actor = sample_actor()
        genre = sample_genre()

        movie.actors.add(actor)
        movie.genres.add(genre)

        result = self.client.get(MOVIE_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(result.status_code, status.HTTP_200_OK)
        self.assertEqual(result.data, serializer.data)

    def test_filter_by_genres(self):
        movie_without_genres = sample_movie()
        movie_with_genre_1 = sample_movie(title="movie_1", description="test", duration=100)
        movie_with_genre_2 = sample_movie(title="movie_2", description="test", duration=150)

        genre_1 = sample_genre(name="genre_1")
        genre_2 = sample_genre(name="genre_2")

        movie_with_genre_1.genres.add(genre_1)
        movie_with_genre_2.genres.add(genre_2)

        res = self.client.get(MOVIE_URL, {
            "genres": f"{genre_1.id},{genre_2.id}"
        })

        serializer_without_genres = MovieListSerializer(movie_without_genres)
        serializer_movie_genres_1 = MovieListSerializer(movie_with_genre_1)
        serializer_movie_genres_2 = MovieListSerializer(movie_with_genre_2)

        self.assertIn(serializer_movie_genres_1.data, res.data)
        self.assertIn(serializer_movie_genres_2.data, res.data)
        self.assertNotIn(serializer_without_genres, res.data)


    def test_filter_movies_by_actors(self):
        movie_without_actors = sample_movie()
        movie_with_actor_1 = sample_movie(title="movie_1")
        movie_with_actor_2 = sample_movie(title="movie_2")

        actor_1 = sample_actor(first_name="John", last_name="Black")
        actor_2 = sample_actor(first_name="John", last_name="White")

        movie_with_actor_1.actors.add(actor_1)
        movie_with_actor_2.actors.add(actor_2)

        res = self.client.get(MOVIE_URL, {
            "actors": f"{actor_1.id},{actor_2.id}"
        })
        serializer_without_actors = MovieListSerializer(movie_without_actors)
        serializer_movie_actors_1 = MovieListSerializer(movie_with_actor_1)
        serializer_movie_actors_2 = MovieListSerializer(movie_with_actor_2)

        self.assertIn(serializer_movie_actors_1.data, res.data)
        self.assertIn(serializer_movie_actors_2.data, res.data)
        self.assertNotIn(serializer_without_actors, res.data)

    def test_movie_detail(self):
        movie = sample_movie()
        movie.genres.add(sample_genre())
        movie.actors.add(sample_actor())

        url = movie_detail_url(movie_id=movie.id)
        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Test",
            "description": "Description",
            "duration": 200,
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(email="admin.user", password="Qwerty12345!", is_staff=True)
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        genre_1 = sample_genre(name="genre_1")
        genre_2 = sample_genre(name="genre_2")

        actor_1 = sample_actor(first_name="John", last_name="Black")
        actor_2 = sample_actor(first_name="John", last_name="White")

        data = {
            "title": "Test",
            "description": "Description",
            "duration": 100,
            "genres": [genre_1.id, genre_2.id],
            "actors": [actor_1.id, actor_2.id]
        }

        res = self.client.post(MOVIE_URL, data)

        movie = Movie.objects.get(id=res.data["id"])

        genres = movie.genres.all()
        actors = movie.actors.all()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        self.assertEqual(res.data["title"], data["title"])
        self.assertEqual(res.data["description"], data["description"])
        self.assertEqual(res.data["duration"], data["duration"])

        self.assertIn(genre_1, genres)
        self.assertIn(genre_2, genres)
        self.assertEqual(genres.count(), 2)

        self.assertIn(actor_1, actors)
        self.assertIn(actor_2, actors)
        self.assertEqual(actors.count(), 2)
