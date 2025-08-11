from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

MOVIE_URL = reverse("cinema:movie-list")


def create_movie(**params):
    defaults = {
        "title": "Test Movie",
        "duration": 20,
        "description": "test description"
    }
    defaults.update(params)

    return Movie.objects.create(**defaults)


def detail_url(movie_id: int) -> reverse:
    return reverse("cinema:movie-detail", args=[movie_id])


class TestUnauthenticatedMovieApi(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required_user(self):
        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedUserMovieApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "user@user.ua",
            "test12345"
        )
        self.client.force_authenticate(self.user)

    def test_auth_required_user(self):
        genres = Genre.objects.create(
            name="TestGenre"
        )
        actor = Actor.objects.create(
            first_name="Test",
            last_name="Testovich"
        )

        create_movie()
        movie_with_genre = create_movie()
        movie_with_actor = create_movie()
        movie_with_genre_actor = create_movie()
        movie_with_genre.genres.add(genres)
        movie_with_actor.actors.add(actor)
        movie_with_genre_actor.actors.add(actor)
        movie_with_genre_actor.genres.add(genres)

        res = self.client.get(MOVIE_URL)

        movie = Movie.objects.all()

        serializer = MovieListSerializer(movie, many=True)

        self.assertEqual(res.data, serializer.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_movie_filter_by_genre(self):
        movie1 = create_movie(title="Movie 1")
        movie2 = create_movie(title="Movie 2")
        movie3 = create_movie(title="Movie 3")

        genre1 = Genre.objects.create(name="GenreTest 1")
        genre2 = Genre.objects.create(name="GenreTest 2")

        movie1.genres.add(genre1)
        movie2.genres.add(genre2)
        movie3.genres.add(genre1, genre2)

        movie_without_genre = create_movie(title="without genre Movie")

        res = self.client.get(MOVIE_URL, {"genres": f"{genre1.id}"})

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie3)
        serializer4 = MovieListSerializer(movie_without_genre)

        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer3.data, res.data)
        self.assertNotIn(serializer2.data, res.data)
        self.assertNotIn(serializer4.data, res.data)

    def test_movie_filter_by_actors(self):
        movie1 = create_movie(title="Movie 1")
        movie2 = create_movie(title="Movie 2")
        movie3 = create_movie(title="Without actor")

        actor1 = Actor.objects.create(
            first_name="Test1",
            last_name="Testovich1",
        )
        actor2 = Actor.objects.create(
            first_name="Test2",
            last_name="Testovich2",
        )
        movie1.actors.add(actor1)
        movie2.actors.add(actor2)

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie3)

        res = self.client.get(
            MOVIE_URL, {"actors": f"{actor1.id}, {actor2.id}"}
        )
        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_movie_filter_by_title(self):
        movie1 = create_movie(title="Movie 1")
        movie2 = create_movie(title="Movie 2")

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)

        res = self.client.get(
            MOVIE_URL, {"title": "Movie 1"}
        )

        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

    def test_retrieve_movie(self):
        movie = create_movie()
        movie.genres.add(Genre.objects.create(name="Test_Genre"))

        url = detail_url(movie.id)
        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie(self):
        load = {
            "title": "Test Movie",
            "duration": 20,
            "description": "test description"
        }

        res = self.client.post(MOVIE_URL, load)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class TestAdminMovieApi(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@admin.ua",
            "test12345",
            is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        movie = {
            "title": "Movie Create",
            "duration": 20,
            "description": "test description"
        }

        res = self.client.post(MOVIE_URL, movie)
        movie_get = Movie.objects.get(id=res.data["id"])
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        for key in movie:
            self.assertEqual(movie[key], getattr(movie_get, key))

    def test_create_movie_with_genre_actor(self):
        genre1 = Genre.objects.create(name="Test Genre")
        genre2 = Genre.objects.create(name="Test1 Genre")
        actor1 = Actor.objects.create(
            first_name="Test",
            last_name="Testovich"
        )
        actor2 = Actor.objects.create(
            first_name="Test1",
            last_name="Testovich1"
        )

        movie = {
            "title": "Movie Create",
            "duration": 20,
            "description": "test description",
            "genres": [genre1.id, genre2.id],
            "actors": [actor1.id, actor2.id],
        }

        res = self.client.post(MOVIE_URL, movie)
        movie_get = Movie.objects.get(id=res.data["id"])

        genres = movie_get.genres.all()
        actors = movie_get.actors.all()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        self.assertEqual(genres.count(), 2)
        self.assertEqual(actors.count(), 2)
        self.assertIn(genre1, genres)
        self.assertIn(genre2, genres)
        self.assertIn(actor1, actors)
        self.assertIn(actor2, actors)
