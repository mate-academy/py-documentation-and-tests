from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")


def create_movie(**params):
    default = {
        "title": "Test title",
        "description": "Test description",
        "duration": 2,
    }
    default.update(params)

    return Movie.objects.create(**default)


def detail_movie_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


class UnAuthenticatedCinemaMovieTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedCinemaMovieTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@test.ua",
            "password12345",
        )

        self.client.force_authenticate(self.user)

    def test_list_movie(self):
        create_movie()
        movie_genre_actor = create_movie()

        genre = Genre.objects.create(name="Genre test")
        actor = Actor.objects.create(
            first_name="Timur",
            last_name="Sirbul"
        )

        movie_genre_actor.genres.add(genre)
        movie_genre_actor.actors.add(actor)

        res = self.client.get(MOVIE_URL)

        movie = Movie.objects.all()
        serializer = MovieListSerializer(movie, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movie_by_genre(self):
        movie1 = create_movie()
        movie2 = create_movie()
        movie3 = create_movie()

        genre = Genre.objects.create(name="Genre test")

        movie1.genres.add(genre)
        movie2.genres.add(genre)

        res = self.client.get(MOVIE_URL, {"genres": f"{genre.id}"})

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie3)

        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_filter_movie_by_actor_and_title(self):
        movie1 = create_movie(title="test")
        movie2 = create_movie(title="Odessa")
        movie3 = create_movie(title="Lviv")

        actor = Actor.objects.create(
            first_name="Timur",
            last_name="Sirbul"
        )

        movie1.actors.add(actor)
        movie2.actors.add(actor)

        res = self.client.get(MOVIE_URL, {"actors": f"{actor.id}"})

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie3)

        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_detail_movie(self):
        movie = create_movie()
        actor = Actor.objects.create(
            first_name="Timur",
            last_name="Sirbul"
        )
        genre = Genre.objects.create(name="Genre test")
        movie.genres.add(genre)
        movie.actors.add(actor)

        url = detail_movie_url(movie.id)

        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Test title",
            "description": "Test description",
            "duration": 2,
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminCinemaMovieTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@test.ua",
            "password12345",
            is_staff=True,
        )

        self.client.force_authenticate(self.user)

    def test_creat_movie(self):
        actor = Actor.objects.create(
            first_name="Timur",
            last_name="Sirbul"
        )
        genre = Genre.objects.create(name="Genre test")

        payload = {
            "title": "Test title",
            "description": "Test description",
            "duration": 2,
            "actors": actor.id,
            "genres": genre.id,
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
