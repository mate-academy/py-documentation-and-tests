from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from cinema.models import Movie, Actor, Genre
from cinema.serializers import MovieListSerializer, MovieDetailSerializer, \
    MovieSerializer

MOVIE_URL = reverse("cinema:movie-list")

def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])

def sample_movie(**params) -> Movie:
    defaults = {
        "title": "Test",
        "description": "Test description",
        "duration": "12",
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)

def sample_actor(**params) -> Actor:
    defaults = {
        "first_name": "Test_name",
        "last_name": "Test_last_name",
    }
    defaults.update(params)
    return Actor.objects.create(**defaults)

def sample_genre(**params) -> Genre:
    defaults = {
        "name": "Test_genre",
    }
    defaults.update(params)
    return Genre.objects.create(**defaults)


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
            email="test@test.com", password="testpassword"
        )
        self.client.force_authenticate(self.user)

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_movies_list(self):
        sample_movie()

        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_movie_filtering_by_title(self):
        movie_1 = sample_movie(title="Title1")
        movie_2 = sample_movie(title="Title2")
        res = self.client.get(MOVIE_URL, {"title": "Title1"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)

        expected_movie1_data = MovieListSerializer(movie_1).data
        self.assertIn(expected_movie1_data, res.data)

        unexpected_movie2_data = MovieListSerializer(movie_2).data
        self.assertNotIn(unexpected_movie2_data, res.data)

    def test_movie_filtering_by_genres(self):
        genre1 = sample_genre(name="Action")
        genre2 = sample_genre(name="Comedy")

        movie1 = sample_movie(title="Movie with Action")
        movie2 = sample_movie(title="Movie with Comedy")

        movie1.genres.add(genre1)
        movie2.genres.add(genre2)

        params = {"genres": f"{genre1.id},{genre2.id}"}
        res = self.client.get(MOVIE_URL, params)

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)

        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)

    def test_movie_filtering_by_actors(self):
        actor1 = sample_actor(first_name="Tom", last_name="Hanks")
        actor2 = sample_actor(first_name="Leonardo", last_name="DiCaprio")
        actor3 = sample_actor(first_name="Brad", last_name="Pitt")

        movie1 = sample_movie(title="Movie with Tom")
        movie2 = sample_movie(title="Movie with Leo")
        movie3 = sample_movie(title="Movie with Brad")

        movie1.actors.add(actor1)
        movie2.actors.add(actor2)
        movie3.actors.add(actor3)

        params = {"actors": f"{actor1.id},{actor2.id}"}
        res = self.client.get(MOVIE_URL, params)

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie3)


        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        movie.genres.add(sample_genre())
        movie.actors.add(sample_actor())

        url = detail_url(movie.id)
        res = self.client.get(url)
        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Matrix",
            "description": "sci-fi",
            "duration": 123,
        }
        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class MovieAdminTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@admin.com", password="testpassword", is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        payload = {
            "title": "Matrix",
            "description": "sci-fi",
            "duration": 123,
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        movie = Movie.objects.get(id=res.data["id"])
        for key in ["title", "description", "duration"]:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_create_movie_with_actors(self):
        actor1 = sample_actor()
        actor2 = sample_actor(first_name="Yulia", last_name="Brown")
        payload = {
            "title": "Matrix",
            "description": "sci-fi",
            "duration": 123,
            "actors": [actor1.id, actor2.id],
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        movie = Movie.objects.get(id=res.data["id"])
        actors = movie.actors.all()

        self.assertIn(actor1, actors)
        self.assertIn(actor2, actors)
        self.assertEqual(actors.count(), 2)

    def test_create_movie_with_genres(self):
        genre = sample_genre()
        payload = {
            "title": "Matrix",
            "description": "sci-fi",
            "duration": 123,
            "genres": [genre.id],
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        movie = Movie.objects.get(id=res.data["id"])
        genres = movie.genres.all()

        self.assertIn(genre, genres)
        self.assertEqual(genres.count(), 1)

    def test_delete_movie_not_allowed(self):
        movie = sample_movie()
        url = detail_url(movie_id=movie.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


