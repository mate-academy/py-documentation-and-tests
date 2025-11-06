from django.test import TestCase

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer


MOVIE_URL = reverse("cinema:movie-list")


class UnauthenticateMovieTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(MOVIE_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticateMovieTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@test.com",
            "testpassword",
        )
        self.client.force_authenticate(user=self.user)

    def test_movie_list(self) -> None:
        self.movie = Movie.objects.create(
            title="Test Movie",
            duration=5,
        )
        url = MOVIE_URL
        response = self.client.get(url)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(serializer.data, response.data)

    def test_items_retrieve(self) -> None:
        movie = Movie.objects.create(
            title="Test",
            duration=5,
        )
        url = reverse("cinema:movie-detail", args=[movie.id])
        response = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(serializer.data, response.data)

    def test_filter_movie_by_genre(self) -> None:
        genre_1 = Genre.objects.create(
            name="Test genre",
        )
        movie_with_genre = Movie.objects.create(
            title="Test",
            duration=5,
        )
        movie_without_genre = Movie.objects.create(
            title="No genre",
            duration=6,
        )

        movie_with_genre.genres.add(genre_1)

        response = self.client.get(MOVIE_URL, {"genres": genre_1.id})
        serializer_movie_with_genre = MovieListSerializer(movie_with_genre)
        serializer_movie_without_genre = MovieListSerializer(movie_without_genre)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertIn(serializer_movie_with_genre.data, response.data)
        self.assertNotIn(serializer_movie_without_genre.data, response.data)

    def test_retrive_movie_detail(self) -> None:
        movie = Movie.objects.create(
            title="Test",
            duration=5,
        )
        movie.genres.add(Genre.objects.create(name="Test genre"))

        url = reverse("cinema:movie-detail", args=[movie.id])
        response = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(serializer.data, response.data)

    def test_create_movie_forbidden(self) -> None:
        payload = {"title": "Test", "duration": 5}
        response = self.client.post(MOVIE_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="<EMAIL>",
            password="<PASSWORD>",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.user)

    def test_create_movie_admin(self) -> None:
        genre = Genre.objects.create(name="Test genre")
        actor = Actor.objects.create(first_name="<NAME>", last_name="<NAME>")
        payload = {
            "title": "Test",
            "duration": 5,
            "description": "Test description",
            "genres": [genre.id],
            "actors": [actor.id],
        }

        response = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=response.data["id"])

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(movie.title, payload["title"])
        self.assertIn(genre, movie.genres.all())
        self.assertEqual(movie.actors.count(), 1)
        self.assertCountEqual(movie.actors.all(), [actor])
