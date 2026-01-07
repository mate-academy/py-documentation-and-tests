from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIES_URL = reverse("cinema:movie-list")

def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=(movie_id,))

def sample_movie(**params):
    defaults = {
        "title": "Sample movie",
        "description": "Sample description",
        "duration": 90,
    }
    defaults.update(params)

    return Movie.objects.create(**defaults)


class UnauthenticatedMovieViewsUsers(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIES_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieViewsUsers(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@mail.test",
            password = "testpass12345"
        )
        self.client.force_authenticate(self.user)


    def test_movies_list(self):
        sample_movie()
        movie_with_genres = sample_movie()

        genre_1 = Genre.objects.create(name="drama")
        genre_2 = Genre.objects.create(name="horror")

        movie_with_genres.genres.add(genre_1, genre_2)

        res = self.client.get(MOVIES_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(serializer.data, res.data)

    def test_filter_movies_with_genre(self):
        movie_without_genre = sample_movie()
        movie_with_genre_1 = sample_movie(title="Test movie 1")
        movie_with_genre_2 = sample_movie(title="Test movie 2")
        genre_1 = Genre.objects.create(name="Comedy")
        genre_2 = Genre.objects.create(name="Thriller")
        movie_with_genre_1.genres.add(genre_1)
        movie_with_genre_2.genres.add(genre_2)

        res = self.client.get(MOVIES_URL, {"genres": f"{genre_1.id},{genre_2.id}"})

        serializer_without_genre = MovieListSerializer(movie_without_genre)
        serializer_with_genre_1 = MovieListSerializer(movie_with_genre_1)
        serializer_with_genre_2 = MovieListSerializer(movie_with_genre_2)

        self.assertIn(serializer_with_genre_1.data, res.data)
        self.assertIn(serializer_with_genre_2.data, res.data)
        self.assertNotIn(serializer_without_genre.data, res.data)

    def test_filter_movies_with_actors(self):
        movie_without_actor = sample_movie()
        movie_with_actor_1 = sample_movie(title="Test movie 1")
        movie_with_actor_2 = sample_movie(title="Test movie 2")
        actor_1 = Actor.objects.create(first_name="first", last_name="first")
        actor_2 = Actor.objects.create(first_name="second", last_name="second")
        movie_with_actor_1.actors.add(actor_1)
        movie_with_actor_2.actors.add(actor_2)

        res = self.client.get(MOVIES_URL, {"actors": f"{actor_1.id},{actor_2.id}"})

        serializer_without_actor = MovieListSerializer(movie_without_actor)
        serializer_with_actor_1 = MovieListSerializer(movie_with_actor_1)
        serializer_with_actor_2 = MovieListSerializer(movie_with_actor_2)

        self.assertIn(serializer_with_actor_1.data, res.data)
        self.assertIn(serializer_with_actor_2.data, res.data)
        self.assertNotIn(serializer_without_actor.data, res.data)


    def test_filter_movie_with_title(self):
        movie_1 = sample_movie(title="Star Wars")
        movie_2 = sample_movie(title="Star Trek")
        movie_3 = sample_movie(title="Harry Potter")

        res = self.client.get(MOVIES_URL, {"title": "Star"})

        serializer_1 = MovieListSerializer(movie_1)
        serializer_2 = MovieListSerializer(movie_2)
        serializer_3 = MovieListSerializer(movie_3)

        self.assertIn(serializer_1.data, res.data)
        self.assertIn(serializer_2.data, res.data)
        self.assertNotIn(serializer_3.data, res.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        genre_1 = Genre.objects.create(name="drama")
        movie.genres.add(genre_1)

        url = detail_url(movie.id)

        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(serializer.data, res.data)

    def test_create_movie_forbidden_if_not_admin(self):
        payload = {
            "title": "test movie",
            "description": "test test",
            "duration": 85
        }

        res = self.client.post(MOVIES_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

class AdminBusTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@admin.test",
            password = "testpass12345",
            is_staff = True
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        genre_1 = Genre.objects.create(name="drama")
        actor_1 = Actor.objects.create(first_name="first", last_name="first")

        payload = {
            "title": "test movie",
            "description": "test test",
            "duration": 85,
            "actors": [actor_1.id],
            "genres": [genre_1.id],
        }

        res = self.client.post(MOVIES_URL, payload)

        movie = Movie.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        for key in ["title", "description", "duration"]:
            self.assertEqual(payload[key], getattr(movie, key))

        self.assertEqual(list(movie.actors.values_list('id', flat=True)),
                         payload['actors'])
        self.assertEqual(list(movie.genres.values_list('id', flat=True)),
                         payload['genres'])
