from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient
from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")


class UnauthenticatedMovieTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


def sample_movie(**params) -> Movie:
    default = {
        "title": "test",
        "description": "test",
        "duration": 100,
    }
    default.update(params)
    return Movie.objects.create(**default)


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


class AuthenticatedMovieTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="tast@test.test", password="test"
        )
        self.client.force_authenticate(self.user)

    def test_movies_list(self):
        movie_with_genre_and_actor = sample_movie()

        genre = Genre.objects.create(name="test")
        actor = Actor.objects.create(first_name="test", last_name="test")

        movie_with_genre_and_actor.genres.add(genre)
        movie_with_genre_and_actor.actors.add(actor)

        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_genres(self):
        movie_without_genre = sample_movie()
        movie_with_genre_1 = sample_movie(title="test_1")
        movie_with_genre_2 = sample_movie(title="test_2")

        genre_1 = Genre.objects.create(name="genre_1")
        genre_2 = Genre.objects.create(name="genre_2")

        movie_with_genre_1.genres.add(genre_1)
        movie_with_genre_2.genres.add(genre_2)

        res = self.client.get(
            MOVIE_URL, {"genres": f"{genre_1.id}, {genre_2.id}"}
        )

        serializer_movie_without_genre = MovieListSerializer(movie_without_genre, many=False)
        serializer_movie_with_genre_1 = MovieListSerializer(movie_with_genre_1, many=False)
        serializer_movie_with_genre_2 = MovieListSerializer(movie_with_genre_2, many=False)

        self.assertIn(serializer_movie_with_genre_1.data, res.data)
        self.assertIn(serializer_movie_with_genre_2.data, res.data)
        self.assertNotIn(serializer_movie_without_genre.data, res.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        movie.genres.add(Genre.objects.create(name="genre_1"))
        url = detail_url(movie.id)

        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {"title": "test", "description": "test", "duration": 100, }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            email="test@test.@test",
            password="test"
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        payload = {"title": "test", "description": "test", "duration": 100}

        res = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_create_movie_with_genres(self):
        genre_1 = Genre.objects.create(name="genre_1")
        genre_2 = Genre.objects.create(name="genre_2")

        payload = {"title": "test", "description": "test", "duration": 100, "genres": [genre_1.id, genre_2.id]}

        res = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(id=res.data["id"])
        genres = movie.genres.all()
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn(genre_1, genres)
        self.assertIn(genre_2, genres)
        self.assertEqual(genres.count(), 2)
