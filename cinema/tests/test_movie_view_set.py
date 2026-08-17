from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer


BASE_URL = reverse("cinema:movie-list")


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=(movie_id,))


def sample_movie(genre, actor, **params) -> Movie:
    defaults = {
        "title": "Test movie",
        "description": "Test",
        "duration": 120,
    }
    defaults.update(params)

    movie = Movie.objects.create(**defaults)
    movie.genres.add(genre)
    movie.actors.add(actor)

    return movie


class TestMovieViewSetAsAnon(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(BASE_URL)

        self.assertEqual(
            res.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )


class TestMovieViewSetAsUser(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.user = get_user_model().objects.create_user(
            "test@test.com",
            "test1234test",
        )

        self.client.force_authenticate(user=self.user)

    def test_auth_access_permission(self):
        genre = Genre.objects.create(name="Drama")
        actor = Actor.objects.create(
            first_name="Test",
            last_name="Example",
        )

        sample_movie(genre, actor)

        res = self.client.get(BASE_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(
            res.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            res.data,
            serializer.data,
        )

    def test_filter_movie_by_genres(self):
        genre_1 = Genre.objects.create(name="Drama")
        genre_2 = Genre.objects.create(name="Action")
        genre_3 = Genre.objects.create(name="Comedy")

        actor_1 = Actor.objects.create(
            first_name="Actor",
            last_name="One",
        )
        actor_2 = Actor.objects.create(
            first_name="Actor",
            last_name="Two",
        )
        actor_3 = Actor.objects.create(
            first_name="Actor",
            last_name="Three",
        )

        movie_1 = sample_movie(
            genre_1,
            actor_1,
            title="Movie one",
        )
        movie_2 = sample_movie(
            genre_2,
            actor_2,
            title="Movie two",
        )
        movie_3 = sample_movie(
            genre_3,
            actor_3,
            title="Movie three",
        )

        res = self.client.get(
            BASE_URL,
            {
                "genres": f"{genre_1.id},{genre_2.id}",
            },
        )

        serializer_1 = MovieListSerializer(movie_1)
        serializer_2 = MovieListSerializer(movie_2)
        serializer_3 = MovieListSerializer(movie_3)

        self.assertIn(
            serializer_1.data,
            res.data,
        )
        self.assertIn(
            serializer_2.data,
            res.data,
        )
        self.assertNotIn(
            serializer_3.data,
            res.data,
        )

    def test_filter_movie_by_actors(self):
        genre_1 = Genre.objects.create(name="Drama")
        genre_2 = Genre.objects.create(name="Action")
        genre_3 = Genre.objects.create(name="Comedy")

        actor_1 = Actor.objects.create(
            first_name="Actor",
            last_name="One",
        )
        actor_2 = Actor.objects.create(
            first_name="Actor",
            last_name="Two",
        )
        actor_3 = Actor.objects.create(
            first_name="Actor",
            last_name="Three",
        )

        movie_1 = sample_movie(
            genre_1,
            actor_1,
            title="Movie one",
        )
        movie_2 = sample_movie(
            genre_2,
            actor_2,
            title="Movie two",
        )
        movie_3 = sample_movie(
            genre_3,
            actor_3,
            title="Movie three",
        )

        res = self.client.get(
            BASE_URL,
            {
                "actors": f"{actor_1.id},{actor_2.id}",
            },
        )

        serializer_1 = MovieListSerializer(movie_1)
        serializer_2 = MovieListSerializer(movie_2)
        serializer_3 = MovieListSerializer(movie_3)

        self.assertIn(
            serializer_1.data,
            res.data,
        )
        self.assertIn(
            serializer_2.data,
            res.data,
        )
        self.assertNotIn(
            serializer_3.data,
            res.data,
        )

    def test_filter_movie_by_title(self):
        genre = Genre.objects.create(name="Drama")

        actor_1 = Actor.objects.create(
            first_name="Actor",
            last_name="One",
        )
        actor_2 = Actor.objects.create(
            first_name="Actor",
            last_name="Two",
        )

        movie_1 = sample_movie(
            genre,
            actor_1,
            title="Harry Potter",
        )
        movie_2 = sample_movie(
            genre,
            actor_2,
            title="The Matrix",
        )

        res = self.client.get(
            BASE_URL,
            {"title": "Harry"},
        )

        serializer_1 = MovieListSerializer(movie_1)
        serializer_2 = MovieListSerializer(movie_2)

        self.assertIn(
            serializer_1.data,
            res.data,
        )
        self.assertNotIn(
            serializer_2.data,
            res.data,
        )

    def test_retrieve_movie_detail(self):
        genre = Genre.objects.create(name="Drama")
        actor = Actor.objects.create(
            first_name="Test",
            last_name="Example",
        )

        movie = sample_movie(genre, actor)

        url = detail_url(movie.id)
        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(
            res.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            res.data,
            serializer.data,
        )

    def test_create_movie_forbidden(self):
        payload = {
            "title": "New movie",
            "description": "Test",
            "duration": 120,
            "genres": [],
            "actors": [],
        }

        res = self.client.post(
            BASE_URL,
            payload,
        )

        self.assertEqual(
            res.status_code,
            status.HTTP_403_FORBIDDEN,
        )


class AdminMovieTest(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.user = get_user_model().objects.create_user(
            "admin@test.com",
            "admin1234admin",
            is_staff=True,
        )

        self.client.force_authenticate(user=self.user)

    def test_admin_create_movie(self):
        genre = Genre.objects.create(name="Drama")
        actor = Actor.objects.create(
            first_name="Test",
            last_name="Example",
        )

        payload = {
            "title": "New movie",
            "description": "Test description",
            "duration": 120,
            "genres": [genre.id],
            "actors": [actor.id],
        }

        res = self.client.post(
            BASE_URL,
            payload,
        )

        self.assertEqual(
            res.status_code,
            status.HTTP_201_CREATED,
        )

        movie = Movie.objects.get(id=res.data["id"])

        self.assertEqual(
            movie.title,
            payload["title"],
        )
        self.assertEqual(
            movie.description,
            payload["description"],
        )
        self.assertEqual(
            movie.duration,
            payload["duration"],
        )

        self.assertIn(
            genre,
            movie.genres.all(),
        )
        self.assertIn(
            actor,
            movie.actors.all(),
        )

        self.assertEqual(
            Movie.objects.count(),
            1,
        )
