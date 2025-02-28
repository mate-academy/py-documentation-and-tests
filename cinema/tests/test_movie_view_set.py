from unittest import TestCase

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

URL_LIST = reverse("cinema:movie-list")


def sample_movie(**params) -> Movie:
    defaults = {
        "title": "Test Movie",
        "description": "Test Movie Description",
        "duration": 60,
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)


class UnauthorizedUserApiTest(TestCase):
    def test_auth_required(self):
        self.client = APIClient()
        res = self.client.get(URL_LIST)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthorizedUserApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.test",
            password="testpassword",
        )
        self.client.force_authenticate(user=self.user)

    def tearDown(self):
        self.user.delete()

    def test_movies_list(self):
        sample_movie()
        res = self.client.get(URL_LIST)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_genres(self):
        movie_without_genres = sample_movie()
        movie_with_genre_1 = sample_movie(title="Test Movie")
        movie_with_genre_2 = sample_movie(title="Test Movie 2")

        genre_1 = Genre.objects.create(name="Genre1")
        genre_2 = Genre.objects.create(name="Genre2")

        movie_with_genre_1.genres.add(genre_1)
        movie_with_genre_2.genres.add(genre_2)

        serializer_without_genre = MovieListSerializer(movie_without_genres)
        serializer_with_genre_1 = MovieListSerializer(movie_with_genre_1)
        serializer_with_genre_2 = MovieListSerializer(movie_with_genre_2)

        res = self.client.get(
            URL_LIST, {"genres": f"{genre_1.id}, {genre_2.id}"}
        )  # ?genres=1,2

        self.assertNotIn(serializer_without_genre.data, res.data)
        self.assertIn(serializer_with_genre_1.data, res.data)
        self.assertIn(serializer_with_genre_2.data, res.data)

    def test_filter_movies_by_actors(self):
        movie_without_actors = sample_movie()
        movie_with_actors_1 = sample_movie(title="Test Movie")
        movie_with_actors_2 = sample_movie(title="Test Movie 2")

        actors_1 = Actor.objects.create(first_name="actors1", last_name="actors1")
        actors_2 = Actor.objects.create(first_name="actors2", last_name="actors2")

        movie_with_actors_1.actors.add(actors_1)
        movie_with_actors_2.actors.add(actors_2)

        serializer_without_actors = MovieListSerializer(movie_without_actors)
        serializer_with_actors_1 = MovieListSerializer(movie_with_actors_1)
        serializer_with_actors_2 = MovieListSerializer(movie_with_actors_2)

        res = self.client.get(
            URL_LIST, {"actors": f"{actors_1.id}, {actors_2.id}"}
        )  # ?actors=1,2

        self.assertNotIn(serializer_without_actors.data, res.data)
        self.assertIn(serializer_with_actors_1.data, res.data)
        self.assertIn(serializer_with_actors_2.data, res.data)

    def test_movie_by_title(self):
        movie_1 = sample_movie()
        movie_2 = sample_movie(title="Test Movie 1")
        movie_3 = sample_movie(title="Test Movie 2")

        serializer_movie_1 = MovieListSerializer(movie_1)
        serializer_movie_2 = MovieListSerializer(movie_2)
        serializer_movie_3 = MovieListSerializer(movie_3)

        res = self.client.get(
            URL_LIST, {"title": f"{movie_2.title}"}
        )  # ?title=Test Movie 1
        res_1 = self.client.get(
            URL_LIST, {"title": f"{movie_3.title}"}
        )  # ?title=Test Movie 2

        self.assertIn(serializer_movie_2.data, res.data)
        self.assertIn(serializer_movie_3.data, res_1.data)
        self.assertNotIn(serializer_movie_1.data, res.data)
        self.assertNotIn(serializer_movie_1.data, res_1.data)

    def test_retrieve_movie(self):
        movie = sample_movie()
        res = self.client.get(reverse("cinema:movie-detail", kwargs={"pk": movie.id}))
        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(serializer.data, res.data)

    def test_admin_required_for_upload_images(self):
        movie = sample_movie()
        res = self.client.get(reverse("cinema:movie-upload-image", args=[movie.id]))
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Test Movie 1",
            "description": "Test Movie Description",
            "duration": 60,
        }
        res = self.client.post(URL_LIST, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class TestAdminUserApiUser(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@test.test",
            password="adminpassword",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.user)

    def tearDown(self):
        self.user.delete()
        Genre.objects.all().delete()
        Actor.objects.all().delete()

    def test_create_movie(self):
        payload = {
            "title": "Test Movie 1",
            "description": "Test Movie Description",
            "duration": 60,
        }
        res = self.client.post(URL_LIST, payload)
        movie = Movie.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_create_movie_with_genres(self):
        genre_1 = Genre.objects.create(name="Genre1")
        genre_2 = Genre.objects.create(name="Genre2")

        payload = {
            "title": "Test Movie 1",
            "description": "Test Movie Description",
            "duration": 60,
            "genres": [genre_1.id, genre_2.id],
        }

        res = self.client.post(URL_LIST, payload)
        movie = Movie.objects.get(id=res.data["id"])
        genres = movie.genres.all()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn(genre_1, genres)
        self.assertIn(genre_2, genres)
        self.assertEqual(movie.genres.count(), 2)

    def test_create_movie_with_actors(self):
        actor_1 = Actor.objects.create(first_name="actor1", last_name="actor1")
        actor_2 = Actor.objects.create(first_name="actor2", last_name="actor2")

        payload = {
            "title": "Test Movie 1",
            "description": "Test Movie Description",
            "duration": 60,
            "actors": [actor_1.id, actor_2.id],
        }

        res = self.client.post(URL_LIST, payload)
        movie = Movie.objects.get(id=res.data["id"])
        actors = movie.actors.all()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn(actor_1, actors)
        self.assertIn(actor_2, actors)
        self.assertEqual(movie.actors.count(), 2)
