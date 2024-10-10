from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieSerializer, MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")

def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])

def sample_movie(**params) -> Movie:
    defaults = {
        "title": "The Great Brick",
        "description": "The Great Brick fall on superman head",
        "duration": 121
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)


class TestUnauthenticatedUser(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class TestAuthenticatedUser(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user1@cinema.com",
            password="2wsxcvfr4",
        )
        self.client.force_authenticate(self.user)

        self.movie = sample_movie()
        self.comedy_movie = sample_movie(title="The Great Brick 2")
        self.drama_movie = sample_movie(title="The Great Brick 3")

        self.genre_1 = Genre.objects.create(name="Comedy")
        self.genre_2 = Genre.objects.create(name="Drama")

        self.actor_1 = Actor.objects.create(
            first_name="Adam",
            last_name="Smith",
        )
        self.actor_2 = Actor.objects.create(
            first_name="Eva",
            last_name="Smith",
        )

        self.comedy_movie.genres.add(self.genre_1)
        self.drama_movie.genres.add(self.genre_2)

        self.comedy_movie.actors.add(self.actor_1)
        self.drama_movie.actors.add(self.actor_2)

        self.payload = {
            "title": "The Great Brick 4",
            "description": "The Great Brick fall on superman head",
            "duration": 121,
        }

    def test_movie_list(self):
        self.client.force_authenticate(self.user)
        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_genres(self):
        self.client.force_authenticate(self.user)
        res = self.client.get(
            MOVIE_URL, {"genres": f"{self.genre_1.id},{self.genre_2.id}"}
        )

        serializer = MovieListSerializer(self.movie)
        serializer_with_genre_1 = MovieListSerializer(self.comedy_movie)
        serializer_with_genre_2 = MovieListSerializer(self.drama_movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertNotIn(serializer.data, res.data)
        self.assertIn(serializer_with_genre_1.data, res.data)
        self.assertIn(serializer_with_genre_2.data, res.data)

    def test_filter_movies_by_actors(self):
        self.client.force_authenticate(self.user)
        res = self.client.get(
            MOVIE_URL, {"actors": f"{self.actor_1.id},{self.actor_2.id}"}
        )

        serializer = MovieListSerializer(self.movie)
        serializer_with_actor_1 = MovieListSerializer(self.comedy_movie)
        serializer_with_actor_2 = MovieListSerializer(self.drama_movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertNotIn(serializer.data, res.data)
        self.assertIn(serializer_with_actor_1.data, res.data)
        self.assertIn(serializer_with_actor_2.data, res.data)

    def test_retrieve_movie_detail(self):
        self.client.force_authenticate(self.user)
        url = detail_url(self.movie.id)
        res = self.client.get(url)

        serializer = MovieDetailSerializer(self.movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        self.client.force_authenticate(self.user)
        res = self.client.post(MOVIE_URL, self.payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class TestAdminUser(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = get_user_model().objects.create_superuser(
            email="admin@cinema.com",
            password="3edcvbgt5",
        )
        self.client.force_authenticate(self.admin)

        self.movie = sample_movie()
        self.comedy_movie = sample_movie(title="The Great Brick 2")
        self.drama_movie = sample_movie(title="The Great Brick 3")

        self.genre_1 = Genre.objects.create(name="Comedy")
        self.genre_2 = Genre.objects.create(name="Drama")

        self.actor_1 = Actor.objects.create(
            first_name="Adam",
            last_name="Smith",
        )
        self.actor_2 = Actor.objects.create(
            first_name="Eva",
            last_name="Smith",
        )

        self.comedy_movie.genres.add(self.genre_1)
        self.drama_movie.genres.add(self.genre_2)

        self.comedy_movie.actors.add(self.actor_1)
        self.drama_movie.actors.add(self.actor_2)

        self.payload = {
            "title": "The Great Brick 4",
            "description": "The Great Brick fall on superman head",
            "duration": 121,
        }

    def test_create_movie(self):
        self.client.force_authenticate(self.admin)
        res = self.client.post(MOVIE_URL, self.payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        movie = Movie.objects.get(pk=res.data["id"])

        for key in self.payload:
            self.assertEqual(self.payload[key], getattr(movie, key))

    def test_admin_create_movie_with_genres_and_actors(self):
        self.client.force_authenticate(self.admin)
        self.payload["genres"] = [self.genre_1.id, self.genre_2.id]
        self.payload["actors"] = [self.actor_1.id, self.actor_2.id]
        res = self.client.post(MOVIE_URL, self.payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        movie = Movie.objects.get(pk=res.data["id"])
        genres = movie.genres.all()
        actors = movie.actors.all()

        self.assertIn(self.genre_1, genres)
        self.assertIn(self.genre_2, genres)
        self.assertEqual(genres.count(), 2)

        self.assertIn(self.actor_1, actors)
        self.assertIn(self.actor_2, actors)
        self.assertEqual(actors.count(), 2)

    def test_delete_movie_not_allowed(self):
        self.client.force_authenticate(self.admin)
        url = detail_url(self.movie.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
