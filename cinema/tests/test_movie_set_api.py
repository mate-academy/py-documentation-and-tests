from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from cinema.models import Movie, Genre, Actor
from cinema.serializers import (
    MovieListSerializer,
    MovieDetailSerializer
)

MOVIE_URL = reverse("cinema:movie-list")


def sample_movie(**params):
    defaults = {
        "title": "Test title",
        "description": "Test description",
        "duration": 120,
    }

    defaults.update(params)

    return Movie.objects.create(**defaults)


def detail_url(movie_id: int):
    return reverse("cinema:movie-detail", args=[movie_id])


class UnauthenticatedMovieAPITest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieAPITest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@test.com",
            "testpass",
        )
        self.client.force_authenticate(self.user)

    def test_access_allowed(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_list_movie(self):
        sample_movie()

        res = self.client.get(MOVIE_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movie_by_genre(self):
        genre1 = Genre.objects.create(name="Test1")
        genre2 = Genre.objects.create(name="Test2")

        movie1 = sample_movie(title="first movie")
        movie2 = sample_movie(title="second movie")
        movie = sample_movie(title="no genre added")

        movie1.genres.add(genre1)
        movie2.genres.add(genre2)

        res = self.client.get(MOVIE_URL, {"genres": f"{movie1.id}, {movie2.id}"})

        serializer = MovieListSerializer(movie)
        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)

        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer.data, res.data)

    def test_filter_movie_by_actor(self):
        actor = Actor.objects.create(first_name="Ricardo",
                                     last_name="Alonso")

        movie1 = sample_movie(title="first movie")
        movie = sample_movie(title="no actor added")

        movie1.actors.add(actor)

        res = self.client.get(MOVIE_URL, {"actors": f"{movie1.id}"})

        serializer = MovieListSerializer(movie)
        serializer1 = MovieListSerializer(movie1)

        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer.data, res.data)

    def test_filter_movie_by_title(self):
        movie1 = sample_movie(title="first movie")
        movie2 = sample_movie(title="second movie")

        res = self.client.get(MOVIE_URL, {"title": "first"})

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)

        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        genre = Genre.objects.create(name="Test1")
        actor = Actor.objects.create(first_name="Ricardo",
                                     last_name="Alonso")

        movie.genres.add(genre)
        movie.actors.add(actor)

        url = detail_url(movie.id)
        result = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(result.status_code, status.HTTP_200_OK)
        self.assertEqual(result.data, serializer.data)

    def test_create_movie_forbidden(self):
        genre = Genre.objects.create(name="Test1")
        actor = Actor.objects.create(first_name="Ricardo",
                                     last_name="Alonso")

        load_data = {
            "title": "Test title",
            "description": "Test description",
            "duration": 120,
            "genre": [genre.id, ],
            "actors": [actor.id, ],
        }

        res = self.client.post(MOVIE_URL, load_data)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieAPITest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@admin.com",
            "1qazcde3",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        genre = Genre.objects.create(name="Test")
        actor = Actor.objects.create(first_name="Ricardos",
                                     last_name="Alonso")

        load_data = {
            "title": "Test title",
            "description": "Test description",
            "duration": 120,
            "genres": [genre.id, ],
            "actors": [actor.id, ],
        }

        res = self.client.post(MOVIE_URL, load_data)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_create_check_content(self):
        genre = Genre.objects.create(name="Test1")
        genre1 = Genre.objects.create(name="Test2")
        actor = Actor.objects.create(first_name="Ricardo",
                                     last_name="Alonso")
        actor1 = Actor.objects.create(first_name="Ricardo",
                                      last_name="Alonso's")
        load_data = {
            "title": "Test title",
            "description": "Test description",
            "duration": 120,
            "genres": [genre.id, genre1.id],
            "actors": [actor.id, actor1.id],
        }

        res = self.client.post(MOVIE_URL, load_data)
        movie = Movie.objects.get(id=res.data["id"])
        genres = movie.genres.all()
        actors = movie.actors.all()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(genres.count(), 2)
        self.assertIn(genre1, genres)
        self.assertEqual(actors.count(), 2)
        self.assertIn(actor1, actors)

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

    def test_upload_image_page(self):
        movie = sample_movie()
        url = reverse("cinema:movie-upload-image", args=[movie.id])

        res = self.client.post(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
