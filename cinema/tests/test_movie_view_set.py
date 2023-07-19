from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")


def some_movie(**params):
    defaults = {
        "title": "Titanic",
        "description": "American epic romance",
        "duration": 2,
    }
    defaults.update(params)

    return Movie.objects.create(**defaults)


def detail_url(movie_id: int):
    return reverse("cinema:movie-detail", args=[movie_id])


class UnauthenticatedMovieTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "user@user.com",
            "123456",
        )
        self.client.force_authenticate(self.user)

    def test_list_movies(self):
        some_movie()
        movie_with_actors = some_movie()
        movie_with_actors_genres = some_movie()

        genre1 = Genre.objects.create(name="drama")
        genre2 = Genre.objects.create(name="detective")

        actor1 = Actor.objects.create(first_name="Frank", last_name="Riz")
        actor2 = Actor.objects.create(first_name="Terrie", last_name="Williams")

        movie_with_actors.actors.add(actor1, actor2)
        movie_with_actors_genres.actors.add(actor1, actor2)
        movie_with_actors_genres.genres.add(genre1, genre2)
        res = self.client.get(MOVIE_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_movie_filter(self):
        movie_sample = some_movie()
        movie1 = some_movie()
        movie2 = some_movie()

        genre = Genre.objects.create(name="drama")

        actor = Actor.objects.create(first_name="Frank", last_name="Riz")

        movie1.actors.add(actor)
        movie2.actors.add(actor)
        movie2.genres.add(genre)

        res_actors = self.client.get(MOVIE_URL, {"actors": f"{actor.id}, {actor.id}"})
        res_actors_genres = self.client.get(
            MOVIE_URL, {"actors": f"{actor.id}"}, {"genres": f"{genre.id}"}
        )

        serializer1 = MovieListSerializer(movie_sample)
        serializer2 = MovieListSerializer(movie1)
        serializer3 = MovieListSerializer(movie2)

        self.assertIn(serializer2.data, res_actors.data)
        self.assertIn(serializer3.data, res_actors_genres.data)
        self.assertNotIn(serializer1.data, res_actors.data)
        self.assertNotIn(serializer1.data, res_actors_genres.data)

    def test_retrieve_movie_detail(self):
        movie = some_movie()
        movie.actors.add(
            Actor.objects.create(first_name="Terrie", last_name="Williams")
        )
        movie.genres.add(Genre.objects.create(name="detective"))

        url = detail_url(movie.id)
        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def create_movie_forbidden(self):
        payload = {"title": "Movie", "description": "Info about movie", "duration": 2}

        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@admin.com",
            "78901234",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)

    def test_create_movie_actors_genres(self):
        genre = Genre.objects.create(name="drama")
        actor = Actor.objects.create(first_name="Frank", last_name="Riz")

        payload = {
            "title": "Movie",
            "description": "Info about movie",
            "duration": 2,
            "genres": genre.id,
            "actors": actor.id,
        }

        res = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=res.data["id"])
        genres = movie.genres.all()
        actors = movie.actors.all()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(genres.count(), 1)
        self.assertIn(genre, genres)
        self.assertEqual(actors.count(), 1)
        self.assertIn(actor, actors)

    def test_delete_not_allowed(self):
        movie = some_movie()
        url = detail_url(movie.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
