from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer


MOVIE_URL = reverse("cinema:movie-list")


def sample_movie(**params):
    defaults = {
        "title": "Sample movie",
        "description": "Sample description",
        "duration": 90,
    }
    defaults.update(params)

    return Movie.objects.create(**defaults)


def sample_genre(**params):
    defaults = {
        "name": "Action",
    }
    defaults.update(params)

    return Genre.objects.create(**defaults)


def sample_actor(**params):
    defaults = {
        "first_name": "Steven",
        "last_name": "Stifmeister",
    }
    defaults.update(params)

    return Actor.objects.create(**defaults)


def detail_url(movie_id: int):
    return reverse("cinema:movie-detail", args=[movie_id])


class UnauthenticatedMovieApiTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test123@test.com",
            "testpas12345",
        )
        self.client.force_authenticate(self.user)

    def test_list_movies(self):
        sample_movie()

        res = self.client.get(MOVIE_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_list_movies_with_genre(self):

        movie1 = sample_movie(title="Titanic")
        movie2 = sample_movie(title="Game")
        genre1 = sample_genre(name="Drama")
        genre2 = sample_genre(name="Action")
        movie1.genres.add(genre1)
        movie2.genres.add(genre2)

        res = self.client.get(MOVIE_URL)
        serializer = MovieListSerializer(
            sorted([movie1, movie2],
                   key=lambda movie: movie.title),
            many=True,
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_list_movies_with_actors(self):

        movie1 = sample_movie(title="Titanic")
        movie2 = sample_movie(title="Game")
        actor1 = sample_actor(
            first_name="Leonardo",
            last_name="DiCaprio",
        )
        actor2 = sample_actor(
            first_name="Kate",
            last_name="Winslet",
        )
        actor3 = sample_actor(
            first_name="Billy",
            last_name="Zane",
        )
        movie1.actors.add(actor1, actor2)
        movie2.actors.add(actor1, actor3)
        res = self.client.get(MOVIE_URL)

        serializer = MovieListSerializer(
            sorted([movie1, movie2],
                   key=lambda movie: movie.title),
            many=True,
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_title(self):

        movie = sample_movie(title="Titanic")
        res = self.client.get(MOVIE_URL, {"title": "Titanic"})
        serializer = MovieListSerializer(movie)
        self.assertIn(serializer.data, res.data)

    def test_filter_movies_by_genre(self):

        movie1 = sample_movie(title="Game")
        movie2 = sample_movie(title="The Godfather")
        movie3 = sample_movie(title="Avatar")

        genre1 = sample_genre(name="Action")
        genre2 = sample_genre(name="Crime")
        genre3 = sample_genre(name="Sci-Fi")

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

        movie1 = sample_movie(title="Titanic")
        movie2 = sample_movie(title="The Godfather")
        actor1 = sample_actor(
            first_name="Leonardo",
            last_name="DiCaprio",
        )
        actor2 = sample_actor(
            first_name="Kate",
            last_name="Winslet",
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

        movie1 = sample_movie(title="Titanic")
        movie2 = sample_movie(title="The Godfather")
        actor1 = sample_actor(
            first_name="Leonardo",
            last_name="DiCaprio",
        )
        actor2 = sample_actor(
            first_name="Al",
            last_name="Pacino",
        )
        genre1 = sample_genre(name="Drama")
        genre2 = sample_genre(name="Crime")

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

        movie = sample_movie(title="Titanic")
        genre = sample_genre(name="Drama")
        actor1 = sample_actor(
            first_name="Leonardo",
            last_name="DiCaprio",
        )
        actor2 = sample_actor(
            first_name="Kate",
            last_name="Winslet",
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
            "title": "Zoo",
            "description": "About animals",
            "duration": 69,
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@test.com",
            "testpas6789",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)
        self.genre1 = sample_genre(name="Documental")
        self.genre2 = sample_genre(name="Adventure")
        self.actor1 = sample_actor(
            first_name="Leonardo",
            last_name="DiCaprio",
        )
        self.actor2 = sample_actor(
            first_name="Kate",
            last_name="Winslet",
        )

    def test_create_movie(self):

        payload = {
            "title": "Earth",
            "description": "About our planet",
            "duration": 99,
        }
        res = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_create_movie_with_actors_and_genres(self):
        payload = {
            "title": "Earth",
            "description": "About our planet",
            "duration": 99,
            "genres": [self.genre1.id, self.genre2.id],
            "actors": [self.actor1.id, self.actor2.id]
        }

        res = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(id=res.data["id"])
        genres = movie.genres.all()
        actors = movie.actors.all()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(genres.count(), 2)
        self.assertIn(self.genre1, genres)
        self.assertIn(self.genre2, genres)
        self.assertEqual(actors.count(), 2)
        self.assertIn(self.actor1, actors)
        self.assertIn(self.actor2, actors)

    def test_delete_movie_not_allowed(self):

        movie = sample_movie()
        url = detail_url(movie.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_update_movie_not_allowed(self):

        movie = sample_movie()
        url = detail_url(movie.id)

        res = self.client.put(url)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
