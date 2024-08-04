from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from cinema.models import Movie, Actor, Genre
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


def sample_movie(**params) -> Movie:
    defaults = {
        "title": "Love in big city",
        "description": "like all",
        "duration": 120,
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)


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
            email="test@test.test",
            password="testtest"
        )
        self.client.force_authenticate(self.user)

    def test_movies_list(self):
        sample_movie()
        movie_with_actors = sample_movie()

        actor_1 = Actor.objects.create(first_name="Gryy", last_name="Neymar")
        actor_2 = Actor.objects.create(first_name="Franchesko", last_name="Totti")

        movie_with_actors.actors.add(actor_1, actor_2)

        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_actors(self):
        movie_without_actors = sample_movie()
        movie_with_actor_1 = sample_movie(title="testmovie22")
        movie_with_actor_2 = sample_movie(title="testmovie33")

        actor_1 = Actor.objects.create(first_name="Gryy", last_name="Neymar")
        actor_2 = Actor.objects.create(first_name="Franchesko", last_name="Totti")

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
        movie_with_genre_1 = sample_movie(title="testmovie22")
        movie_with_genre_2 = sample_movie(title="testmovie23")

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

    def test_filter_movies_by_title(self):
        movie_1 = sample_movie(title="testmovie1")
        movie_2 = sample_movie(title="testmovie2")

        res = self.client.get(
            MOVIE_URL,
            {"title": "testmovie2"}
        )

        serializer_movie_1 = MovieListSerializer(movie_1)
        serializer_movie_2 = MovieListSerializer(movie_2)

        self.assertIn(serializer_movie_2.data, res.data)
        self.assertNotIn(serializer_movie_1.data, res.data)
        self.assertEqual(len(res.data), 1)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        movie.genres.add(Genre.objects.create(name="genre1"))
        movie.genres.add(Genre.objects.create(name="genre2"))
        movie.actors.add(Actor.objects.create(first_name="Gryy", last_name="Neymar"))
        movie.actors.add(Actor.objects.create(first_name="Franchesko", last_name="Totti"))

        url = detail_url(movie.id)

        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)


class AdminMovieTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@test.test",
            password="testtest",
            is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        genre_1 = Genre.objects.create(name="genre1")
        genre_2 = Genre.objects.create(name="genre2")
        actor_1 = Actor.objects.create(first_name="Gryy", last_name="Neymar")

        payload = {
            "title": "TestMovieTitle1",
            "description": "The legend is returning",
            "duration": 120,
            "genres": [genre_1.id, genre_2.id],
            "actors": [actor_1.id],
        }

        res = self.client.post(MOVIE_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        movie = Movie.objects.get(id=res.data["id"])

        genres = movie.genres.all()
        actors = movie.actors.all()

        self.assertEqual(list(genres.values_list('id', flat=True)), sorted(payload["genres"]))
        self.assertEqual(list(actors.values_list('id', flat=True)), sorted(payload["actors"]))

        self.assertEqual(movie.title, payload["title"])
        self.assertEqual(movie.description, payload["description"])
        self.assertEqual(movie.duration, payload["duration"])

    def test_create_movie_with_actors(self):
        actor_1 = Actor.objects.create(first_name="Alan", last_name="Way")
        actor_2 = Actor.objects.create(first_name="Keydan", last_name="Rey")
        genre_1 = Genre.objects.create(name="Genre1")
        genre_2 = Genre.objects.create(name="Genre2")

        payload = {
            "title": "TestMovieTitle1",
            "description": "The legend is returning",
            "duration": 120,
            "actors": [actor_1.id, actor_2.id],
            "genres": [genre_1.id, genre_2.id]
        }

        res = self.client.post(MOVIE_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        movie = Movie.objects.get(id=res.data["id"])

        actors = movie.actors.all()
        genres = movie.genres.all()

        self.assertIn(actor_1, actors)
        self.assertIn(actor_2, actors)
        self.assertEqual(actors.count(), 2)

        self.assertIn(genre_1, genres)
        self.assertIn(genre_2, genres)
        self.assertEqual(genres.count(), 2)

    def test_delete_movie_not_allowed(self):
        movie = sample_movie()

        url = detail_url(movie.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
