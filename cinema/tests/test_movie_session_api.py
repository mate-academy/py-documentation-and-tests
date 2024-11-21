from django.test import TestCase
from django.contrib.auth import get_user_model

from rest_framework.test import APIClient
from rest_framework.reverse import reverse
from rest_framework import status

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")


def detail_url(movie_id: int) -> str:
    return reverse("cinema:movie-detail", args=(movie_id,))


def sample_movie(**params) -> Movie:
    defaults = {
        "title": "Groundhog Day",
        "description": "A narcissistic, self-centered weatherman finds himself in a time loop on Groundhog Day.",
        "duration": 101,
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)


class UnauthenticatedCinemaApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedCinemaApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test_user@test.com",
            password="testpassword"
        )
        self.client.force_authenticate(self.user)

    def test_movie_list(self):
        sample_movie()
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movie_by_genre(self):
        movie_without_genres = sample_movie(
            title="test title",
            description="test description",
            duration=100
        )
        genre_1 = Genre.objects.create(name="Comedy")
        genre_2 = Genre.objects.create(name="Drama")
        genre_3 = Genre.objects.create(name="Fantasy")
        genre_4 = Genre.objects.create(name="Romance")
        movie_with_genres = sample_movie()
        movie_with_genres.genres.add(
            genre_1,
            genre_2,
            genre_3,
            genre_4,
        )
        res = self.client.get(MOVIE_URL, data={"genres": f"{genre_1.id},{genre_2.id},{genre_3.id}"})
        serializer_movie_with_genres = MovieListSerializer(movie_with_genres)
        serializer_movie_without_genres = MovieListSerializer(movie_without_genres)
        self.assertIn(serializer_movie_with_genres.data, res.data)
        self.assertNotIn(serializer_movie_without_genres.data, res.data)

    def test_filter_movie_by_title(self):
        movie_test_title = sample_movie(
            title="test title",
            description="test description",
            duration=100
        )
        sample_movie()

        res = self.client.get(MOVIE_URL, data={"title": "Groundhog Day"})
        serializer_movie_default_title = MovieListSerializer(Movie.objects.get(title="Groundhog Day"))
        serializer_movie_with_test_title = MovieListSerializer(movie_test_title)
        self.assertIn(serializer_movie_default_title.data, res.data)
        self.assertNotIn(serializer_movie_with_test_title.data, res.data)

    def test_filter_movie_by_actors(self):
        movie_without_actors = sample_movie(
            title="test title",
            description="test description",
            duration=100
        )
        actor_1 = Actor.objects.create(first_name="Bill", last_name="Murray")
        actor_2 = Actor.objects.create(first_name="Andie", last_name="MacDowell")
        movie_with_actors = sample_movie()
        movie_with_actors.actors.add(
            actor_1,
            actor_2,
        )
        res = self.client.get(MOVIE_URL, data={"actors": f"{actor_1.id},{actor_2.id}"})
        serializer_movie_with_actors = MovieListSerializer(movie_with_actors)
        serializer_movie_without_actors = MovieListSerializer(movie_without_actors)
        self.assertIn(serializer_movie_with_actors.data, res.data)
        self.assertNotIn(serializer_movie_without_actors.data, res.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        url = detail_url(movie.id)
        res = self.client.get(url)
        serializer = MovieDetailSerializer(movie)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Test title",
            "description": "Test description",
            "duration": 123,
        }
        res = self.client.post(path=MOVIE_URL, data=payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@admin.com",
            password="testpassword",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        Genre.objects.create(name="Comedy")
        payload = {
            "title": "Test title",
            "description": "Test description",
            "duration": 123,
        }
        res = self.client.post(path=MOVIE_URL, data=payload)
        movie = Movie.objects.get(id=res.data["id"])
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_create_movie_with_genres(self):
        genre_1 = Genre.objects.create(name="Comedy")
        genre_2 = Genre.objects.create(name="Drama")
        genre_3 = Genre.objects.create(name="Fantasy")
        genre_4 = Genre.objects.create(name="Romance")
        payload = {
            "title": "Test title",
            "description": "Test description",
            "duration": 123,
            "genres": [genre_1.id, genre_2.id, genre_3.id, genre_4.id]
        }
        res = self.client.post(path=MOVIE_URL, data=payload)
        movie = Movie.objects.get(id=res.data["id"])
        genres = Genre.objects.all()
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn(genre_1, genres)
        self.assertIn(genre_2, genres)
        self.assertIn(genre_3, genres)
        self.assertIn(genre_4, genres)
        self.assertEqual(genres.count(), 4)


