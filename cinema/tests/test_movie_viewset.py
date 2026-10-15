from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import Actor, Genre, Movie
from cinema.serializers import MovieDetailSerializer, MovieListSerializer

MOVIE_URL = reverse("cinema:movie-list")
TOKEN_URL = reverse("user:token_obtain_pair")


def sample_movie(**params):
    defaults = {
        "title": "Sample movie",
        "description": "Sample description",
        "duration": 90,
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)


def sample_genre(**params):
    defaults = {"name": "Drama"}
    defaults.update(params)
    return Genre.objects.create(**defaults)


def sample_actor(**params):
    defaults = {"first_name": "George", "last_name": "Clooney"}
    defaults.update(params)
    return Actor.objects.create(**defaults)


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


class UnauthenticatedMovieViewSetTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()

    def tearDown(self):
        cache.clear()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieViewSetTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "user@cinema.com",
            "password123",
        )
        self.client.force_authenticate(self.user)

    def tearDown(self):
        cache.clear()

    def test_list_movies(self):
        movie1 = sample_movie(title="Movie 1")
        movie2 = sample_movie(title="Movie 2")
        genre = sample_genre()
        actor = sample_actor()
        movie1.genres.add(genre)
        movie1.actors.add(actor)

        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.prefetch_related("genres", "actors")
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_by_title(self):
        movie1 = sample_movie(title="Inception")
        movie2 = sample_movie(title="Interstellar")
        movie3 = sample_movie(title="Avatar")

        res = self.client.get(MOVIE_URL, {"title": "in"})

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie3)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_filter_by_genres(self):
        movie1 = sample_movie(title="Movie 1")
        movie2 = sample_movie(title="Movie 2")
        movie3 = sample_movie(title="Movie 3")

        genre1 = sample_genre(name="Action")
        genre2 = sample_genre(name="Comedy")

        movie1.genres.add(genre1)
        movie2.genres.add(genre2)

        res = self.client.get(MOVIE_URL, {"genres": f"{genre1.id}"})

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie3)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

        res_multiple = self.client.get(
            MOVIE_URL,
            {"genres": f"{genre1.id},{genre2.id}"},
        )
        self.assertIn(serializer1.data, res_multiple.data)
        self.assertIn(serializer2.data, res_multiple.data)
        self.assertNotIn(serializer3.data, res_multiple.data)

    def test_filter_by_actors(self):
        movie1 = sample_movie(title="Movie 1")
        movie2 = sample_movie(title="Movie 2")
        movie3 = sample_movie(title="Movie 3")

        actor1 = sample_actor(first_name="Brad", last_name="Pitt")
        actor2 = sample_actor(first_name="Tom", last_name="Hanks")

        movie1.actors.add(actor1)
        movie2.actors.add(actor2)

        res = self.client.get(MOVIE_URL, {"actors": f"{actor1.id}"})

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie3)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

        res_multiple = self.client.get(
            MOVIE_URL,
            {"actors": f"{actor1.id},{actor2.id}"},
        )
        self.assertIn(serializer1.data, res_multiple.data)
        self.assertIn(serializer2.data, res_multiple.data)
        self.assertNotIn(serializer3.data, res_multiple.data)

    def test_retrieve_movie(self):
        movie = sample_movie()
        genre = sample_genre()
        actor = sample_actor()
        movie.genres.add(genre)
        movie.actors.add(actor)

        url = detail_url(movie.id)
        res = self.client.get(url)
        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "New Movie",
            "description": "Description",
            "duration": 100,
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_movie(self):
        movie = sample_movie()
        url = detail_url(movie.id)
        payload = {
            "title": "Updated Movie",
            "description": "Updated Description",
            "duration": 120,
        }
        res_put = self.client.put(url, payload)
        self.assertEqual(res_put.status_code, status.HTTP_403_FORBIDDEN)

        res_patch = self.client.patch(url, {"title": "Patched"})
        self.assertEqual(res_patch.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_movie(self):
        movie = sample_movie()
        url = detail_url(movie.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieViewSetTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.admin = get_user_model().objects.create_superuser(
            "admin@cinema.com",
            "password123",
        )
        self.client.force_authenticate(self.admin)

    def tearDown(self):
        cache.clear()

    def test_create_movie(self):
        genre = sample_genre()
        actor = sample_actor()
        payload = {
            "title": "Admin Movie",
            "description": "Admin Description",
            "duration": 110,
            "genres": [genre.id],
            "actors": [actor.id],
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(id=res.data["id"])
        self.assertEqual(movie.title, payload["title"])
        self.assertEqual(movie.duration, payload["duration"])

    def test_create_movie_with_genres_and_actors(self):
        genre1 = sample_genre(name="Action")
        genre2 = sample_genre(name="Drama")
        actor1 = sample_actor(first_name="Leonardo", last_name="DiCaprio")
        actor2 = sample_actor(first_name="Brad", last_name="Pitt")

        payload = {
            "title": "Featured Movie",
            "description": "Featured Description",
            "duration": 150,
            "genres": [genre1.id, genre2.id],
            "actors": [actor1.id, actor2.id],
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        movie = Movie.objects.get(id=res.data["id"])
        genres = movie.genres.all()
        actors = movie.actors.all()

        self.assertEqual(genres.count(), 2)
        self.assertIn(genre1, genres)
        self.assertIn(genre2, genres)

        self.assertEqual(actors.count(), 2)
        self.assertIn(actor1, actors)
        self.assertIn(actor2, actors)

    def test_create_movie_invalid(self):
        payload = {
            "title": "",
            "duration": 90,
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_movie(self):
        movie = sample_movie()
        url = detail_url(movie.id)
        payload = {
            "title": "Updated by Admin",
            "description": "Updated Description",
            "duration": 130,
        }
        res_put = self.client.put(url, payload)
        self.assertEqual(
            res_put.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def test_delete_movie(self):
        movie = sample_movie()
        url = detail_url(movie.id)
        res = self.client.delete(url)
        self.assertEqual(
            res.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )


class JwtAuthTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "jwt.user@cinema.com",
            "password123",
        )

    def tearDown(self):
        cache.clear()

    def test_jwt_auth(self):
        res = self.client.post(
            TOKEN_URL,
            {
                "email": "jwt.user@cinema.com",
                "password": "password123",
            },
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("access", res.data)
        self.assertIn("refresh", res.data)

        access_token = res.data["access"]
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
        )

        movie_res = self.client.get(MOVIE_URL)
        self.assertEqual(movie_res.status_code, status.HTTP_200_OK)

