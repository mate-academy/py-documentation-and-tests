from django.contrib.auth import get_user_model
from django.test import TestCase

from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from cinema.models import Movie, Actor, Genre
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")

def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=(movie_id,))

def sample_movie(**params) -> Movie:
    defaults = {
        "title": "Test Movie",
        "description": "Test Movie Description",
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


class UnauthenticatedMovieViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
            res = self.client.get(MOVIE_URL)
            self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="example@gmail.com",
            password="strong_password",
        )
        self.client.force_authenticate(self.user, [])

    def test_movies_list(self):
        sample_movie()

        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)


        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_actors(self):
        movie_without_actor = sample_movie()
        movie_with_actor_1 = sample_movie(title="Test Movie 1")
        movie_with_actor_2 = sample_movie(title="Test Movie 2")

        actor_1 = sample_actor()
        actor_2 = sample_actor(first_name="Kevin")

        movie_with_actor_1.actors.add(actor_1)
        movie_with_actor_2.actors.add(actor_2)

        res = self.client.get(
            MOVIE_URL, {"actors": f"{actor_1.id},{actor_2.id}"}
        )

        serializer_without_actor = MovieListSerializer(movie_without_actor)
        serializer_with_actor_1 = MovieListSerializer(movie_with_actor_1)
        serializer_with_actor_2 = MovieListSerializer(movie_with_actor_2)

        self.assertIn(serializer_with_actor_1.data, res.data)
        self.assertIn(serializer_with_actor_2.data, res.data)
        self.assertNotIn(serializer_without_actor.data, res.data)

    def test_filter_movies_by_genres(self):
        movie_without_genre = sample_movie()
        movie_with_genre_1 = sample_movie(title="Test Movie 1")
        movie_with_genre_2 = sample_movie(title="Test Movie 2")

        genre_1 = Genre.objects.create(name="Drama")
        genre_2 = Genre.objects.create(name="Sci-Fi")

        movie_with_genre_1.genres.add(genre_1)
        movie_with_genre_2.genres.add(genre_2)

        res = self.client.get(
            MOVIE_URL, {"genres": f"{genre_1.id},{genre_2.id}"}
        )

        serializer_without_genre = MovieListSerializer(movie_without_genre)
        serializer_with_genre_1 = MovieListSerializer(movie_with_genre_1)
        serializer_with_genre_2 = MovieListSerializer(movie_with_genre_2)

        self.assertIn(serializer_with_genre_1.data, res.data)
        self.assertIn(serializer_with_genre_2.data, res.data)
        self.assertNotIn(serializer_without_genre.data, res.data)

    def test_filter_movies_by_all(self):
        movie_without_all = sample_movie()
        movie_with_all_1 = sample_movie(title="First Movie")
        movie_with_all_2 = sample_movie(title="Find new book")

        genre_1 = Genre.objects.create(name="Comedy")
        genre_2 = Genre.objects.create(name="Fantasy")
        actor_1 = sample_actor()
        actor_2 = sample_actor(first_name="Kevin")

        movie_with_all_1.genres.add(genre_1, genre_2)
        movie_with_all_2.genres.add(genre_2)
        movie_with_all_1.actors.add(actor_1)
        movie_with_all_2.actors.add(actor_2)

        res = self.client.get(
            MOVIE_URL, {
                "genres": f"{genre_1.id},{genre_2.id}",
                "title": "Fi",
                "actors": f"{actor_1.id}",
            }
        )

        serializer_without_all = MovieListSerializer(movie_without_all)
        serializer_with_all_1 = MovieListSerializer(movie_with_all_1)
        serializer_with_all_2 = MovieListSerializer(movie_with_all_2)

        self.assertIn(serializer_with_all_1.data, res.data)
        self.assertNotIn(serializer_with_all_2.data, res.data)
        self.assertNotIn(serializer_without_all.data, res.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        movie.actors.add(sample_actor())

        url = detail_url(movie.id)

        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Test Movie 1",
            "description": "Test Movie Description"
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@gmail.com",
            password="strong_password",
            is_staff=True,
        )
        self.client.force_authenticate(self.user, [])

    def test_create_movie(self):
        payload = {
            "title": "Test Movie",
            "description": "Test Movie Description",
            "duration": 120
        }

        res = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_create_movie_with_actors_and_genres(self):
        actor_1 = sample_actor()
        actor_2 = sample_actor(first_name="Kevin")

        payload = {
            "title": "Test Movie",
            "description": "Test Movie Description",
            "duration": 120,
            "actors": [actor_1.id, actor_2.id],
        }

        res = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(id=res.data["id"])
        actors = movie.actors.all()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn(actor_1, actors)
        self.assertIn(actor_2, actors)
        self.assertEqual(actors.count(), 2)

    def test_delete_movie_not_allowed(self):
        movie = sample_movie()

        url = detail_url(movie.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
