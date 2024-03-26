from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")


def sample_movie(**params):
    default = {
        "title": "Spider man",
        "description": "test description",
        "duration": 3,
    }
    default.update(params)

    return Movie.objects.create(**default)


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=(movie_id,))


class UnauthenticatedMovieApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.test",
            password="test_password"
        )
        self.client.force_authenticate(self.user)

    def test_movies_list_access(self):
        sample_movie()

        res = self.client.get(MOVIE_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.data, serializer.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_filter_movies_by_title(self):
        movie_with_title1 = sample_movie()
        movie_with_title2 = sample_movie(title="Titanic")

        res = self.client.get(
            MOVIE_URL,
            {"title": movie_with_title1}
        )

        serializer_with_movie_title1 = MovieListSerializer(movie_with_title1)
        serializer_with_movie_title2 = MovieListSerializer(movie_with_title2)

        self.assertIn(serializer_with_movie_title1.data, res.data)
        self.assertNotIn(serializer_with_movie_title2.data, res.data)

    def test_filter_movies_by_genres(self):
        movie_without_genre = sample_movie()
        movie_with_genre = sample_movie(title="Titanic")

        genre = Genre.objects.create(name="drama")

        movie_with_genre.genres.add(genre)

        res = self.client.get(
            MOVIE_URL,
            {"genres": genre.id}
        )

        serializer_movie_with_genre = MovieListSerializer(movie_with_genre)
        serializer_without_genre = MovieListSerializer(movie_without_genre)

        self.assertIn(serializer_movie_with_genre.data, res.data)
        self.assertNotIn(serializer_without_genre.data, res.data)

    def test_filter_movies_by_actors(self):
        movie_without_actor = sample_movie()
        movie_with_actor1 = sample_movie(title="Titanic")
        movie_with_actor2 = sample_movie(title="New")


        actor1 = Actor.objects.create(first_name="John", last_name="Doe")
        actor2 = Actor.objects.create(first_name="Mark", last_name="One")

        movie_with_actor1.actors.add(actor1)
        movie_with_actor2.actors.add(actor2)

        res = self.client.get(
            MOVIE_URL,
            {"actors": f"{actor1.id}, {actor2.id}"}
        )

        serializer_movie_with_actor1 = MovieListSerializer(movie_with_actor1)
        serializer_movie_with_actor2 = MovieListSerializer(movie_with_actor2)
        serializer_without_actors = MovieListSerializer(movie_without_actor)

        self.assertIn(serializer_movie_with_actor1.data, res.data)
        self.assertIn(serializer_movie_with_actor2.data, res.data)
        self.assertNotIn(serializer_without_actors.data, res.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        movie.genres.add(Genre.objects.create(name="Formula 1"))

        url = detail_url(movie.id)

        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_forbidden(self):
        payload = {
            "title": "Wor",
            "description": "test description",
            "duration": 34,
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@admin.admin",
            password="test_password",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        payload = {
            "title": "Wor",
            "description": "test description",
            "duration": 34,
        }

        res = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_create_movie_with_actors_and_genres(self):
        actor = Actor.objects.create(first_name="John", last_name="Doe")
        genre = Genre.objects.create(name="drama")

        payload = {
            "title": "Wor",
            "description": "test description",
            "duration": 34,
            "actors": [actor.id],
            "genres": [genre.id],
        }

        res = self.client.post(MOVIE_URL, payload)

        actors = Actor.objects.all()
        genres = Genre.objects.all()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn(actor, actors)
        self.assertIn(genre, genres)
