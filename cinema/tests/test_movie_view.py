from django.contrib.auth import get_user_model
from django.test import (TestCase)
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieDetailSerializer, MovieListSerializer

MOVIE_URL = reverse('cinema:movie-list')


def dummy_movie(**params):
    defaults = {
        "title": "test movie",
        "description": "test description",
        "duration": 100,
    }
    defaults.update(params)

    return Movie.objects.create(**defaults)


def detail_url(movie_id: int):
    return reverse("cinema:movie-detail", args=[movie_id])


class UnAuthenticatedMovieAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@test.com",
            "testpass",
        )
        self.client.force_authenticate(self.user)

    def test_list_movies(self):
        dummy_movie()

        res = self.client.get(MOVIE_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_list_movies_with_genre(self):
        movie1 = dummy_movie(title="Test")
        movie2 = dummy_movie(title="TestTest")
        genre1 = Genre.objects.create(name="TestTestTest")
        genre2 = Genre.objects.create(name="TestTestTestTest")
        movie1.genres.add(genre1)
        movie2.genres.add(genre2)
        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_list_movies_with_actors(self):
        movie1 = dummy_movie(title="Test")
        movie2 = dummy_movie(title="TestTestTestTest")
        actor1 = Actor.objects.create(
            first_name="Test1",
            last_name="TestTest1",
        )
        actor2 = Actor.objects.create(
            first_name="Test2",
            last_name="TestTest2",
        )
        actor3 = Actor.objects.create(
            first_name="Test3",
            last_name="TestTest3",
        )
        movie1.actors.add(actor1, actor2)
        movie2.actors.add(actor1, actor3)
        res = self.client.get(MOVIE_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_title(self):
        movie = dummy_movie(title="Test")
        res = self.client.get(MOVIE_URL, {"title": "Test"})
        serializer = MovieListSerializer(movie)
        self.assertIn(serializer.data, res.data)

    def test_filter_movies_by_genre(self):
        movie1 = dummy_movie(title="Test")
        movie2 = dummy_movie(title="TheTest")
        movie3 = dummy_movie(title="TestTest")

        genre1 = Genre.objects.create(name="Test3")
        genre2 = Genre.objects.create(name="Test4")
        genre3 = Genre.objects.create(name="Test5")

        movie1.genres.add(genre1)
        movie2.genres.add(genre2)
        movie3.genres.add(genre3)

        res = self.client.get(
            MOVIE_URL,
            {"genres": f"{genre1.id}"},
        )

        serializer1 = MovieListSerializer(movie1)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer1.data, res.data)
        res = self.client.get(
            MOVIE_URL,
            {"genres": f"{genre1.id},{genre2.id}"},
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertCountEqual(res.data, res.data)

    def test_filter_movies_by_actors(self):
        movie1 = dummy_movie(title="TestTestTest")
        movie2 = dummy_movie(title="TheTest")
        actor1 = Actor.objects.create(
            first_name="Test1",
            last_name="TestTest1",
        )
        actor2 = Actor.objects.create(
            first_name="Test2",
            last_name="TestTest2",
        )
        movie1.actors.add(actor1)
        movie1.actors.add(actor2)
        res = self.client.get(
            MOVIE_URL,
            {"actors": f"{actor1.id}, {actor2.id}"},
        )
        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

    def test_filter_movies_by_genre_and_actor(self):
        movie1 = dummy_movie(title="Test")
        movie2 = dummy_movie(title="TheTest")
        actor1 = Actor.objects.create(
            first_name="Test1",
            last_name="TestTest1",
        )
        actor2 = Actor.objects.create(
            first_name="Test2",
            last_name="TestTest2",
        )
        genre1 = Genre.objects.create(name="Test3")
        genre2 = Genre.objects.create(name="Test4")

        movie1.actors.add(actor1)
        movie2.actors.add(actor2)

        movie1.genres.add(genre1)
        movie2.genres.add(genre2)

        res = self.client.get(
            MOVIE_URL,
            {"genres": f"{genre1.id}", "actors": f"{actor1.id}"},
        )

        serializer1 = MovieListSerializer(movie1)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer1.data, res.data)

        res = self.client.get(
            MOVIE_URL,
            {"genres": f"{genre2.id}", "actors": f"{actor1.id}"},
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertNotIn(serializer1.data, res.data)

    def test_retrieve_movie_detail(self):
        movie = dummy_movie(title="Testanic")
        genre = Genre.objects.create(name="Test")
        actor1 = Actor.objects.create(
            first_name="Test1",
            last_name="TestTest1",
        )
        actor2 = Actor.objects.create(
            first_name="Test2",
            last_name="TestTest2",
        )
        movie.actors.add(actor1)
        movie.actors.add(actor2)
        movie.genres.add(genre)
        url = detail_url(movie.id)
        res = self.client.get(url)
        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(serializer.data, res.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Zoolander",
            "description": "Fashion",
            "duration": 120,
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@test.com",
            "testpass",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)
        self.genre1 = Genre.objects.create(name="Documentary")
        self.genre2 = Genre.objects.create(name="Action")
        self.actor1 = Actor.objects.create(
            first_name="Test1",
            last_name="TestTest1",
        )
        self.actor2 = Actor.objects.create(
            first_name="Test2",
            last_name="TestTest2",
        )

    def test_create_movie(self):
        url = reverse("cinema:movie-list")
        data = {
            "title": "Test",
            "description": "A test description",
            "year": 2000,
            "genres": [self.genre1.id, self.genre2.id],
            "actors": [self.actor1.id, self.actor2.id],
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Movie.objects.count(), 0)

    def test_delete_movie_not_allowed(self):
        movie = dummy_movie()
        url = detail_url(movie.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_update_movie_not_allowed(self):
        movie = dummy_movie()
        url = detail_url(movie.id)

        res = self.client.put(url)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
