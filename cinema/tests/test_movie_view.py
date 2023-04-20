from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from rest_framework.test import APIClient

from cinema.models import Movie, Actor, Genre
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")


def detail_url(movie_id: int):
    return reverse("cinema:movie-detail", args=[movie_id])


def create_movie(**params):
    defaults = {
        "title": "Test movie",
        "description": "Movie about tests",
        "duration": 15
    }
    defaults.update(params)

    return Movie.objects.create(**defaults)


class UnauthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@test.com",
            "pass1423"
        )
        self.client.force_authenticate(self.user)

    def test_list_movies(self):
        create_movie()
        movie_with_actors = create_movie()
        movie_with_genres = create_movie()

        actor = Actor.objects.create(
            first_name="Jimmy",
            last_name="Fallon"
        )
        genre = Genre.objects.create(
            name="Some"
        )
        movie_with_actors.actors.add(actor)
        movie_with_genres.genres.add(genre)

        res = self.client.get(MOVIE_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_actors_and_genres(self):
        movie1 = create_movie(title="Movie 1")
        movie2 = create_movie(title="Movie 2")
        movie3 = create_movie(title="Movie 3")

        actor1 = Actor.objects.create(
            first_name="Jimmy",
            last_name="Fallon"
        )

        actor2 = Actor.objects.create(
            first_name="Vinnie",
            last_name="Jones"
        )

        genre1 = Genre.objects.create(name="genre1")
        genre2 = Genre.objects.create(name="genre2")

        movie1.actors.add(actor1)
        movie2.actors.add(actor2)

        movie1.genres.add(genre1)
        movie2.genres.add(genre2)

        res = self.client.get(MOVIE_URL, {"actors": f"{actor1.id},{actor2.id}"})
        res2 = self.client.get(MOVIE_URL, {"genres": f"{genre1.id},{genre2.id}"})

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie3)

        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)
        self.assertIn(serializer1.data, res2.data)
        self.assertIn(serializer2.data, res2.data)
        self.assertNotIn(serializer3.data, res2.data)

    def test_filter_movies_by_title(self):
        movie1 = create_movie(title="Movie 1")
        movie2 = create_movie(title="Movie 2")

        res = self.client.get(MOVIE_URL, {"title": "2"})

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)

        self.assertNotIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)

    def test_retrieve_movie_detail(self):
        movie = create_movie()

        actor1 = Actor.objects.create(
            first_name="Jimmy",
            last_name="Fallon"
        )
        movie.actors.add(actor1)
        url = detail_url(movie.id)
        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "movie_never_been",
            "description": "sad movie",
            "duration": 0
        }

        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@cinema.com",
            "password1234",
            is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        payload = {
            "title": "movie_never_been",
            "description": "sad_movie",
            "duration": 1
        }

        res = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_create_movie_with_actors(self):
        actor1 = Actor.objects.create(
            first_name="Jimmy",
            last_name="Fallon"
        )

        actor2 = Actor.objects.create(
            first_name="Vinnie",
            last_name="Jones"
        )

        payload = {
            "title": "movie_never_been",
            "description": "sad_movie",
            "duration": 1,
            "actors": [actor1.id, actor2.id]
        }

        res = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(id=res.data["id"])
        actors = movie.actors.all()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(actors.count(), 2)
        self.assertIn(actor1, actors)
        self.assertIn(actor2, actors)
