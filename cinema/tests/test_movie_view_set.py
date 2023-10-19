from django.test import TestCase

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIES_URL = reverse("cinema:movie-list")


def sample_movie(**params):
    defaults = {
        "title": "test_title",
        "description": "test_description",
        "duration": 123,
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)


class UnauthenticatedApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIES_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test2user@tests.test", password="testUser123"
        )
        self.client.force_authenticate(self.user)

    def test_get_expected_list_movies(self):
        sample_movie()
        sample_movie()
        res = self.client.get(MOVIES_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_movie_has_correct_str_display(self):
        sample_movie(title="expected_title")
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)
        self.assertEqual(serializer.data[0]["title"], "expected_title")

    def test_filter_by_genre(self):
        genre1 = Genre.objects.create(name="Drama")
        genre2 = Genre.objects.create(name="Comedy")

        movie1 = sample_movie()
        movie2 = sample_movie()
        movie3 = sample_movie()
        movie4 = sample_movie()

        movie1.genres.set([genre1])
        movie2.genres.set([genre2])
        movie3.genres.set([genre1, genre2])

        res = self.client.get(
            MOVIES_URL, {"genres": f"{genre1.id}, {genre2.id}"}
        )

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie3)
        serializer4 = MovieListSerializer(movie4)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertIn(serializer3.data, res.data)
        self.assertNotIn(serializer4.data, res.data)

    def test_filter_by_actor(self):
        actor1 = Actor.objects.create(first_name="Test", last_name="Tester")
        actor2 = Actor.objects.create(first_name="Te", last_name="Tr")

        movie1 = sample_movie()
        movie2 = sample_movie()
        movie3 = sample_movie()
        movie4 = sample_movie()

        movie1.actors.set([actor1])
        movie2.actors.set([actor2])
        movie3.actors.set([actor1, actor2])

        res = self.client.get(
            MOVIES_URL, {"actors": f"{actor1.id}, {actor2.id}"}
        )

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie3)
        serializer4 = MovieListSerializer(movie4)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertIn(serializer3.data, res.data)
        self.assertNotIn(serializer4.data, res.data)

    def test_filter_by_title(self):
        movie1 = sample_movie(title="title")
        movie2 = sample_movie(title="CoolTitle")
        movie3 = sample_movie(title="title1CoolTitle")
        movie4 = sample_movie(title="not_included")
        res = self.client.get(MOVIES_URL, {"title": "title"})
        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie3)
        serializer4 = MovieListSerializer(movie4)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertIn(serializer3.data, res.data)
        self.assertNotIn(serializer4.data, res.data)

    def test_retrieve(self):
        movie = sample_movie()
        url = reverse("cinema:movie-detail", args=[movie.id])
        res = self.client.get(url)
        serializer = MovieDetailSerializer(movie)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_forbidden(self):
        payload = {
            "title": "test_title",
            "description": "test_description",
            "duration": 123,
        }
        res = self.client.post(MOVIES_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@tests.test",
            password="testUser123",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)

    def test_admin_has_correct_permission_to_post(self):
        actor = Actor.objects.create(first_name="Test", last_name="Actor")
        genre = Genre.objects.create(name="TestGenre")
        payload = {
            "title": "test_title",
            "description": "test_description",
            "duration": 123,
            "actors": [actor.id],
            "genres": [genre.id],
        }
        res = self.client.post(MOVIES_URL, payload)
        movie = Movie.objects.get(id=res.data["id"])
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        for key in payload:
            if key in ["actors", "genres"]:
                saved_ids = list(
                    getattr(movie, key).values_list("id", flat=True)
                )
                self.assertEqual(payload[key], saved_ids)
            else:
                self.assertEqual(payload[key], getattr(movie, key))