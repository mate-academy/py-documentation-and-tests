from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient
from rest_framework.utils.representation import serializer_repr

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieSerializer, MovieListSerializer, MovieDetailSerializer
from cinema.tests.test_movie_api import MOVIE_URL


MOVIE_URL = reverse("cinema:movie-list")

def detail_url(movie_id):
    return reverse("cinema:movie-detail", kwargs={"pk": movie_id})

def sample_movie(**params):
    defaults = {
        "title": "Sample movie",
        "description": "Sample description",
        "duration": 90,
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)

def sample_genre(name="Drama"):
    return Genre.objects.create(name=name)


def sample_actor(first_name="Tom", last_name="Cruise"):
    return Actor.objects.create(first_name=first_name, last_name=last_name)




class UnauthenticatedMovieApiTest(TestCase):
    def setUp(self):
        self.client = Client()


    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.test",
            password="testuserpassword",
        )
        self.client.force_authenticate(self.user)

    def test_movies_list(self):
        sample_movie()
        movie_with_genres = sample_movie()

        genre_1 = Genre.objects.create(name="Action")
        genre_2 = Genre.objects.create(name="Comedy")

        movie_with_genres.genres.add(genre_1, genre_2)

        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"], serializer.data)

    def test_filter_movies_by_genres(self):
        movie_without_genre = sample_movie(title="No Genre")
        movie_with_genre1 = sample_movie(title="Genre One")
        movie_with_genre2 = sample_movie(title="Genre Two")

        genre_1 = Genre.objects.create(name="Action")
        genre_2 = Genre.objects.create(name="Comedy")

        movie_with_genre1.genres.add(genre_1)
        movie_with_genre2.genres.add(genre_2)

        res = self.client.get(
            MOVIE_URL, {"genres": f"{genre_1.id},{genre_2.id}"}
        )

        serializer_without_genre = MovieListSerializer(movie_without_genre)
        serializer_genre1 = MovieListSerializer(movie_with_genre1)
        serializer_genre2 = MovieListSerializer(movie_with_genre2)

        self.assertIn(serializer_genre1.data, res.data["results"])
        self.assertIn(serializer_genre2.data, res.data["results"])
        self.assertNotIn(serializer_without_genre.data, res.data["results"])

    def test_filter_movies_by_actors(self):
        actor_1 = Actor.objects.create(first_name="Tom", last_name="Cruise")
        actor_2 = Actor.objects.create(first_name="Scarlett", last_name="Johansson")

        movie_without_actor = sample_movie(title="No Actor")
        movie_with_actor1 = sample_movie(title="Actor One")
        movie_with_actor2 = sample_movie(title="Actor Two")

        movie_with_actor1.actors.add(actor_1)
        movie_with_actor2.actors.add(actor_2)

        res = self.client.get(MOVIE_URL, {"actors": f"{actor_1.id},{actor_2.id}"})

        serializer_1 = MovieListSerializer(movie_with_actor1)
        serializer_2 = MovieListSerializer(movie_with_actor2)
        serializer_0 = MovieListSerializer(movie_without_actor)

        results = res.data["results"] if "results" in res.data else res.data
        returned_ids = [movie["id"] for movie in results]

        self.assertIn(movie_with_actor1.id, returned_ids)
        self.assertIn(movie_with_actor2.id, returned_ids)
        self.assertNotIn(movie_without_actor.id, returned_ids)

class AuthenticatedMovieDetailTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.test",
            password="testuserpassword",
        )
        self.client.force_authenticate(self.user)

    def test_retrieve_movie_detail_with_genres_and_actors(self):
        movie = sample_movie(title="Detailed Movie")
        genre = sample_genre(name="Action")
        actor = sample_actor(first_name="Scarlett", last_name="Johansson")

        movie.genres.add(genre)
        movie.actors.add(actor)

        url = detail_url(movie.id)
        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Forbidden Movie",
            "description": "Should not be created",
            "duration": 120,
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@dmin.test",
            password="testpassword",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        genre = Genre.objects.create(name="Sci-Fi")
        actor = Actor.objects.create(first_name="Matthew", last_name="McConaughey")

        payload = {
            "title": "Interstellar",
            "description": "Space exploration",
            "duration": 169,
            "genres": [genre.id],
            "actors": [actor.id],
        }

        res = self.client.post(MOVIE_URL, payload)
        print(res.status_code)
        print(res.data)
        movie = Movie.objects.get(id=res.data["id"])

        self.assertEqual(movie.title, payload["title"])
        self.assertEqual(movie.description, payload["description"])
        self.assertEqual(movie.duration, payload["duration"])
        self.assertEqual(
            set(movie.genres.values_list("id", flat=True)),
            set(payload["genres"])
        )
        self.assertEqual(
            set(movie.actors.values_list("id", flat=True)),
            set(payload["actors"])
        )

    def test_create_movie_with_genres_and_actors(self):
        genre_1 = Genre.objects.create(name="Sci-Fi")
        genre_2 = Genre.objects.create(name="Adventure")
        actor_1 = Actor.objects.create(first_name="Matthew", last_name="McConaughey")
        actor_2 = Actor.objects.create(first_name="Anne", last_name="Hathaway")

        payload = {
            "title": "Interstellar",
            "description": "Space exploration",
            "duration": 169,
            "genres": [genre_1.id, genre_2.id],
            "actors": [actor_1.id, actor_2.id],
        }

        res = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(set(movie.genres.values_list("id", flat=True)), set(payload["genres"]))
        self.assertEqual(set(movie.actors.values_list("id", flat=True)), set(payload["actors"]))

    def test_delete_movie_not_allowed(self):
        movie = sample_movie(title="Undeletable Movie")
        url = detail_url(movie.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
