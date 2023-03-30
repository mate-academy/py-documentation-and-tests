from django.test import TestCase

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, Actor, Genre
from cinema.serializers import MovieDetailSerializer, MovieListSerializer

MOVIE_URL = reverse("cinema:movie-list")


def detail_url(movie_id: int) -> str:
    return reverse("cinema:movie-detail", kwargs={"pk": movie_id})


def create_movie(**params) -> Movie:
    movie = {
        "title": "Test",
        "description": "Test description",
        "duration": 11,
    }
    movie.update(params)
    return Movie.objects.create(**movie)


class PrivateMovieViewSetTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "us1er@test.com", "passwordtest123"
        )
        self.client.force_authenticate(self.user)
        self.movie1 = create_movie()
        self.movie2 = create_movie()

    def test_user_can_list_movies(self):
        movies = Movie.objects.all()
        serializer = MovieDetailSerializer(movies, many=True)
        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_user_can_retrieve_movie(self):
        movie = Movie.objects.get(id=self.movie1.id)
        serializer = MovieDetailSerializer(movie, many=False)
        url = detail_url(self.movie1.id)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_title(self) -> None:
        movie3 = create_movie(title="Test1")

        response = self.client.get(MOVIE_URL, {"title": "Test1"})

        serializer1 = MovieListSerializer(self.movie1)
        serializer2 = MovieListSerializer(self.movie2)
        serializer3 = MovieListSerializer(movie3)

        self.assertNotIn(serializer1.data, response.data)
        self.assertNotIn(serializer2.data, response.data)
        self.assertIn(serializer3.data, response.data)

    def test_filter_movies_by_actors(self) -> None:
        actor1 = Actor.objects.create(first_name="first1", last_name="last1")
        actor2 = Actor.objects.create(first_name="firsst1", last_name="lasts1")

        movie3 = create_movie()
        movie3.actors.set([actor1.id, actor2.id])
        serializer1 = MovieListSerializer(self.movie1)
        serializer2 = MovieListSerializer(self.movie2)
        serializer3 = MovieListSerializer(movie3)

        response = self.client.get(MOVIE_URL, {"actors": f"{actor1.id},123"})

        self.assertNotIn(serializer1.data, response.data)
        self.assertNotIn(serializer2.data, response.data)
        self.assertIn(serializer3.data, response.data)

        response = self.client.get(MOVIE_URL, {"actors": "123"})

        self.assertNotIn(serializer1.data, response.data)
        self.assertNotIn(serializer2.data, response.data)
        self.assertNotIn(serializer3.data, response.data)

    def test_filter_movies_by_genres(self) -> None:
        genre1 = Genre.objects.create(name="Genre 1")
        genre2 = Genre.objects.create(name="Genre 2")

        movie3 = create_movie()
        movie3.genres.set([genre1.id, genre2.id])

        serializer1 = MovieListSerializer(self.movie1)
        serializer2 = MovieListSerializer(self.movie2)
        serializer3 = MovieListSerializer(movie3)

        response = self.client.get(MOVIE_URL, {"genres": f"{genre1.id},{genre2.id}"})

        self.assertNotIn(serializer1.data, response.data)
        self.assertNotIn(serializer2.data, response.data)
        self.assertIn(serializer3.data, response.data)

        response = self.client.get(MOVIE_URL, {"genres": "12312"})

        self.assertNotIn(serializer1.data, response.data)
        self.assertNotIn(serializer2.data, response.data)
        self.assertNotIn(serializer3.data, response.data)

    def test_user_can_not_create_movie_(self) -> None:
        context = {
            "title": "Test",
            "description": "Test desc",
            "duration": 123,
        }

        response = self.client.post(MOVIE_URL, context)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.admin = get_user_model().objects.create_user(
            "admin@admin.com", "test_pass", is_staff=True
        )
        self.client.force_authenticate(self.admin)

    def test_create_movie_with_genres_and_actors(self) -> None:
        genre1 = Genre.objects.create(name="Genre 1")
        genre2 = Genre.objects.create(name="Genre 2")
        actor1 = Actor.objects.create(first_name="first1", last_name="last1")
        actor2 = Actor.objects.create(first_name="first2", last_name="last2")
        context = {
            "title": "Test",
            "description": "Test desc",
            "duration": 123,
            "genres": [genre1.id, genre2.id],
            "actors": [actor1.id, actor2.id],
        }
        response = self.client.post(MOVIE_URL, data=context)
        movie = Movie.objects.get(id=response.data["id"])
        genres = movie.genres.all()
        actors = movie.actors.all()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(actors.count(), 2)
        self.assertIn(actor1, actors)
        self.assertIn(actor2, actors)
        self.assertEqual(genres.count(), 2)
        self.assertIn(genre1, genres)
        self.assertIn(genre2, genres)

    def test_delete_movie_not_allowed(self) -> None:
        movie = create_movie()
        url = detail_url(movie.id)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_update_movie_not_allowed(self) -> None:
        movie = create_movie()
        url = detail_url(movie.id)
        context = {
            "title": "Test",
            "description": "Test desc",
            "duration": 123,
        }
        response = self.client.put(url, data=context)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_partial_update_movie_not_allowed(self) -> None:
        movie = create_movie()
        url = detail_url(movie.id)
        context = {
            "title": "TITLE",
        }
        response = self.client.patch(url, data=context)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
