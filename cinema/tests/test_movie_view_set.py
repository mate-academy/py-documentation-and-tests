from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import Actor, Genre, Movie
from cinema.serializers import MovieDetailSerializer, MovieListSerializer

MOVIE_URL = reverse("cinema:movie-list")


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


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
        "name": "Drama",
    }
    defaults.update(params)

    return Genre.objects.create(**defaults)


def sample_actor(**params):
    defaults = {"first_name": "George", "last_name": "Clooney"}
    defaults.update(params)

    return Actor.objects.create(**defaults)


class PublicMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_movie_list(self):
        movie = sample_movie()
        movie.genres.add(sample_genre())
        movie.actors.add(sample_actor())

        res = self.client.get(MOVIE_URL)
        serializer = MovieListSerializer(Movie.objects.all(), many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        movie.genres.add(sample_genre())
        movie.actors.add(sample_actor())

        res = self.client.get(detail_url(movie.id))
        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_requires_authentication(self):
        payload = {
            "title": "Sample movie",
            "description": "Sample description",
            "duration": 90,
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.test",
            password="testpassword",
        )
        self.client.force_authenticate(user=self.user)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Sample movie",
            "description": "Sample description",
            "duration": 90,
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_filter_movie_by_title(self):
        matched_movie = sample_movie(title="Wanted")
        sample_movie(title="Another title")

        res = self.client.get(MOVIE_URL, {"title": "want"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual([movie["id"] for movie in res.data], [matched_movie.id])

    def test_filter_movie_by_genres(self):
        genre1 = sample_genre(name="Drama")
        genre2 = sample_genre(name="Comedy")
        movie1 = sample_movie(title="Drama movie")
        movie2 = sample_movie(title="Comedy movie")
        movie1.genres.add(genre1)
        movie2.genres.add(genre2)

        res = self.client.get(MOVIE_URL, {"genres": str(genre2.id)})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual([movie["id"] for movie in res.data], [movie2.id])

    def test_filter_movie_by_actors(self):
        actor1 = sample_actor(first_name="Keanu", last_name="Reeves")
        actor2 = sample_actor(first_name="Carrie", last_name="Moss")
        movie1 = sample_movie(title="Matrix")
        movie2 = sample_movie(title="Other")
        movie1.actors.add(actor1)
        movie2.actors.add(actor2)

        res = self.client.get(MOVIE_URL, {"actors": str(actor1.id)})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual([movie["id"] for movie in res.data], [movie1.id])


class AdminMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            email="admin@test.test",
            password="testpassword",
        )
        self.client.force_authenticate(user=self.user)

    def test_create_movie(self):
        genre1 = sample_genre(name="Drama")
        genre2 = sample_genre(name="Comedy")
        actor1 = sample_actor(first_name="Keanu", last_name="Reeves")
        actor2 = sample_actor(first_name="Carrie", last_name="Moss")
        payload = {
            "title": "Sample movie",
            "description": "Sample description",
            "duration": 90,
            "genres": [genre1.id, genre2.id],
            "actors": [actor1.id, actor2.id],
        }

        res = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(movie.title, payload["title"])
        self.assertEqual(movie.description, payload["description"])
        self.assertEqual(movie.duration, payload["duration"])
        self.assertSetEqual(
            set(movie.genres.values_list("id", flat=True)),
            set(payload["genres"]),
        )
        self.assertSetEqual(
            set(movie.actors.values_list("id", flat=True)),
            set(payload["actors"]),
        )

    def test_partial_update_movie(self):
        movie = sample_movie()
        genre = sample_genre()
        actor = sample_actor()
        payload = {"genres": [genre.id], "actors": [actor.id]}

        res = self.client.patch(detail_url(movie.id), payload)
        movie.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertSetEqual(set(movie.genres.values_list("id", flat=True)), {genre.id})
        self.assertSetEqual(set(movie.actors.values_list("id", flat=True)), {actor.id})

    def test_delete_movie_not_allowed(self):
        movie = sample_movie()

        res = self.client.delete(detail_url(movie.id))

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
