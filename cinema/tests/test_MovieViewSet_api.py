from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import Movie
from cinema.serializers import MovieListSerializer, MovieDetailSerializer
from cinema.tests.test_movie_api import (
    sample_movie,
    sample_actor,
    sample_genre,
    detail_url,
    MOVIE_URL
)


class UnauthenticatedMovieApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test123@test.com",
            "testpass123"
        )
        self.client.force_authenticate(self.user)

    def test_list_movies(self):
        sample_movie()
        movie_with_actors = sample_movie()
        movie_with_genres = sample_movie()

        movie_with_actors.actors.add(sample_actor())
        movie_with_genres.genres.add(sample_genre())

        res = self.client.get(MOVIE_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_list_movies_with_filtering(self):
        movie_with_title = sample_movie(title="Naruto")
        movie_with_actors = sample_movie()
        movie_with_genres = sample_movie()

        actor = sample_actor(first_name="Noriaki")
        genre = sample_genre(name="Anime")

        movie_with_actors.actors.add(actor)
        movie_with_genres.genres.add(genre)

        filtering_by_title = self.client.get(MOVIE_URL, {"title": "naruto"})
        filtering_by_actor = self.client.get(MOVIE_URL, {"actors": f"{actor.id}"})
        filtering_by_genre = self.client.get(MOVIE_URL, {"genres": f"{genre.id}"})

        serializer_with_title = MovieListSerializer(movie_with_title)
        serializer_with_actor = MovieListSerializer(movie_with_actors)
        serializer_with_genre = MovieListSerializer(movie_with_genres)

        # filtering by title
        self.assertIn(serializer_with_title.data, filtering_by_title.data)
        self.assertNotIn(serializer_with_actor.data, filtering_by_title.data)
        self.assertNotIn(serializer_with_genre.data, filtering_by_title.data)

        # filtering by actor
        self.assertIn(serializer_with_actor.data, filtering_by_actor.data)
        self.assertNotIn(serializer_with_title.data, filtering_by_actor.data)

        # filtering by genre
        self.assertIn(serializer_with_genre.data, filtering_by_genre.data)
        self.assertNotIn(serializer_with_title.data, filtering_by_genre.data)

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
            "title": "Testtest movie",
            "description": "Testtest description",
            "duration": 90,
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@admin.com", "adminpassword1"
        )
        self.client.force_authenticate(self.user)

    def test_create_movie_with_genre_and_actor(self):
        genre1 = sample_genre(name="Anime")
        genre2 = sample_genre(name="Senen")
        actor = sample_actor(first_name="Noriaki", last_name="Sugiyama")
        payload = {
            "title": "Naruto",
            "description": "Naruto: last film",
            "duration": 90,
            "genres": [genre1.id, genre2.id],
            "actors": [actor.id],
        }

        res = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=res.data["id"])
        genres = movie.genres.all()
        actors = movie.actors.all()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(genres.count(), 2)
        self.assertEqual(actors.count(), 1)
        self.assertIn(genre1, genres)
        self.assertIn(genre2, genres)
        self.assertIn(actor, actors)

    def test_delete_movie_not_allowed(self):
        movie = sample_movie()

        url = detail_url(movie.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

