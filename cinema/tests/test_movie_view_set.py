from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")


def detail_movie_url(movie_id: int) -> str:
    return reverse("cinema:movie-detail", kwargs={"pk": movie_id})


def sample_movie(**params) -> Movie:
    defaults = {
        "title": "Interesting movie",
        "description": "Very funny",
        "duration": 58,
    }
    defaults.update(params)

    return Movie.objects.create(**defaults)


class UnAuthenticatedMovieApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self) -> None:
        response = self.client.get(MOVIE_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@test.com",
            "test_pass",
        )
        self.client.force_authenticate(self.user)

    def test_list_movies(self) -> None:
        sample_movie()
        movie_with_genres_actors = sample_movie()
        genre1 = Genre.objects.create(name="Paul")
        genre2 = Genre.objects.create(name="Bob")
        movie_with_genres_actors.genres.add(genre1, genre2)
        actors1 = Actor.objects.create(first_name="Red", last_name="Pork")
        actors2 = Actor.objects.create(first_name="Green", last_name="Cow")
        movie_with_genres_actors.actors.add(actors2, actors1)

        response = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_filter_movies_by_title(self) -> None:
        movie1 = sample_movie(title="Movie 1")
        movie2 = sample_movie(title="Movie 1")
        movie3 = sample_movie(title="Movie 3")

        response = self.client.get(MOVIE_URL, {"title": "Movie 1"})

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie3)

        self.assertIn(serializer1.data, response.data)
        self.assertIn(serializer2.data, response.data)
        self.assertNotIn(serializer3.data, response.data)

    def test_filter_movies_by_actors(self) -> None:
        movie1 = sample_movie(title="Movie1")
        movie2 = sample_movie(title="Movie2")
        actor1 = Actor.objects.create(first_name="first1", last_name="last1")
        actor2 = Actor.objects.create(first_name="first2", last_name="last2")
        movie1.actors.add(actor1)
        movie2.actors.add(actor2)
        movie3 = sample_movie(title="Without actors")
        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie3)

        response = self.client.get(
            MOVIE_URL, {"actors": f"{actor1.id},{actor2.id}"}
        )

        self.assertIn(serializer1.data, response.data)
        self.assertIn(serializer2.data, response.data)
        self.assertNotIn(serializer3.data, response.data)

    def test_filter_movies_by_genres(self) -> None:
        movie1 = sample_movie(title="Movie 1")
        movie2 = sample_movie(title="Movie 2")
        genre1 = Genre.objects.create(name="Genre 1")
        genre2 = Genre.objects.create(name="Genre 2")
        movie1.genres.add(genre1)
        movie2.genres.add(genre2)
        movie3 = sample_movie(title="Without genres")
        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie3)

        response = self.client.get(
            MOVIE_URL, {"genres": f"{genre1.id},{genre2.id}"}
        )

        self.assertIn(serializer1.data, response.data)
        self.assertIn(serializer2.data, response.data)
        self.assertNotIn(serializer3.data, response.data)

    def test_retrieve_movie_detail(self) -> None:
        movie = sample_movie()
        genre1 = Genre.objects.create(name="Genre 1")
        movie.genres.add(genre1)
        actor1 = Actor.objects.create(first_name="first1", last_name="last1")
        movie.actors.add(actor1)

        url = detail_movie_url(movie.id)
        response = self.client.get(url)
        serializer = MovieDetailSerializer(movie)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_create_movie_forbidden(self) -> None:
        payload = {
            "title": "Interesting movie",
            "description": "Very funny",
            "duration": 58,
        }

        response = self.client.post(MOVIE_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@admin.com",
            "test_pass",
            is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self) -> None:
        payload = {
            "title": "Interesting movie",
            "description": "Very funny",
            "duration": 58,
        }

        response = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=response.data["id"])

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_create_movie_with_genres_and_actors(self) -> None:
        genre1 = Genre.objects.create(name="Genre 1")
        genre2 = Genre.objects.create(name="Genre 2")
        actor1 = Actor.objects.create(first_name="first1", last_name="last1")
        actor2 = Actor.objects.create(first_name="first2", last_name="last2")
        payload = {
            "title": "Interesting movie",
            "description": "Very funny",
            "duration": 58,
            "genres": [genre1.id, genre2.id],
            "actors": [actor1.id, actor2.id],
        }
        response = self.client.post(MOVIE_URL, data=payload)
        movie = Movie.objects.get(id=response.data["id"])
        genres = movie.genres.all()
        actors = movie.actors.all()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(genres.count(), 2)
        self.assertIn(genre1, genres)
        self.assertIn(genre2, genres)
        self.assertEqual(actors.count(), 2)
        self.assertIn(actor1, actors)
        self.assertIn(actor2, actors)

    def test_delete_movie_not_allowed(self) -> None:
        movie = sample_movie()
        url = detail_movie_url(movie.id)
        response = self.client.delete(url)
        self.assertEqual(
            response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def test_update_movie_not_allowed(self) -> None:
        movie = sample_movie()
        url = detail_movie_url(movie.id)
        payload = {
            "title": "Interesting movie",
            "description": "Very funny",
            "duration": 58,
        }
        response = self.client.put(url, data=payload)
        self.assertEqual(
            response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def test_partial_update_movie_not_allowed(self) -> None:
        movie = sample_movie()
        url = detail_movie_url(movie.id)
        payload = {
            "title": "TITLE",
        }
        response = self.client.patch(url, data=payload)
        self.assertEqual(
            response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )
