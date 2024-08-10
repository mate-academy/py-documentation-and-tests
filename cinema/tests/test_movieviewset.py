from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from cinema.models import (
    Movie,
    Genre,
    Actor
)
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])

def sample_movie(**params) -> Movie:
    genres = Genre.objects.create(name="Drama")
    actors = Actor.objects.create(first_name="Allan", last_name="Smith")
    default = {
        "title": "My Movie",
        "description": "Very nice movie",
        "duration": 3,
    }
    default.update(params)
    movie = Movie.objects.create(**default)

    movie.genres.set([genres])
    movie.actors.set([actors])

    return movie


class UnauthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(MOVIE_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.test",
            password="testpassword",
        )
        self.client.force_authenticate(self.user)

    def test_movies_list(self):
        sample_movie()

        response = self.client.get(MOVIE_URL)
        # print(response.data)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)


    def test_movies_list_filtred_by_genre(self):
        movie_with_genre = sample_movie()

        genre_1 = Genre.objects.create(name="Novel")
        genre_2 = Genre.objects.create(name="Sci-Fi")

        movie_with_genre.genres.add(genre_1, genre_2)

        response = self.client.get(MOVIE_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)


    def test_movies_list_filtred_by_actor(self):
        movie_with_actor = sample_movie()

        actor_1 = Actor.objects.create(first_name="Alia", last_name="Ram")
        actor_2 = Actor.objects.create(first_name="Oskar", last_name="Smuth")

        movie_with_actor.actors.add(actor_1, actor_2)

        response = self.client.get(MOVIE_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)


    def test_movies_list_filtered_by_movie(self):
        movie_to_filter = Movie.objects.create(
            title="My Movie2",
            description="Amazing movie",
            duration=1,
        )

        genre = Genre.objects.create(name="TestGenre")
        actor = Actor.objects.create(first_name="Nastia", last_name="Nastia")

        other_movie = Movie.objects.create(
            title="Another Movie",
            description="Another amazing movie",
            duration=2,
        )
        other_movie.genres.add(genre)
        other_movie.actors.add(actor)

        response = self.client.get(f"{MOVIE_URL}?id={movie_to_filter.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertTrue(any(movie['id'] == movie_to_filter.id for movie in response_data))


    def test_retrieve_movie_details(self):
        movie = sample_movie()
        movie.genres.add(Genre.objects.create(name="TestGenre2"))
        movie.actors.add(Actor.objects.create(first_name="Mask", last_name="Geraschenkp"))

        url = detail_url(movie.id)

        response = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_movie_create_forbidden(self):
        payload ={
            "title": "My Rest Movie2",
            "description": "Nice movie",
            "duration": 7,
            "genres": [Genre.objects.create(name="TestGenre3")],
            "actors": [Actor.objects.create(first_name="Adel", last_name="Cloony")],
        }

        response = self.client.post(MOVIE_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@admin.test", password="12345test", is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        genre = Genre.objects.create(name="TestGenre4")
        actor = Actor.objects.create(first_name="Adely", last_name="Clony")

        payload = {
            "title": "My Best Movie3",
            "description": "Very nice movie",
            "duration": 9,
            "genres": [genre.id],
            "actors": [actor.id],
        }

        response = self.client.post(MOVIE_URL, payload, format="json")

        movie = Movie.objects.get(id=response.data["id"])
        genres = movie.genres.all()
        actors = movie.actors.all()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn(genre, genres)
        self.assertIn(actor, actors)

    def test_delete_movie(self):
        movie = sample_movie()
        url = detail_url(movie.id)
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
