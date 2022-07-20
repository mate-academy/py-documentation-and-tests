from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")


def detail_url(movie_id: int):
    return reverse("cinema:movie-detail", args=[movie_id])


def sample_movie(**params):
    defaults = {
        "title": "Avengers",
        "description": "Ave Avengers",
        "duration": 143,

    }
    defaults.update(**params)

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
            "t@t.com",
            "tpwd"
        )
        self.client.force_authenticate(self.user)

    def test_list_movies(self):
        sample_movie()
        sample_movie()

        res = self.client.get(MOVIE_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_movies_filtered_by_title(self):
        movie1 = sample_movie(title="Avengers1")
        movie2 = sample_movie(title="Pet Sematary")

        res = self.client.get(MOVIE_URL, {"title": f"{movie1.id}"})

        ser1 = MovieListSerializer(movie1)
        ser2 = MovieListSerializer(movie2)

        self.assertIn(ser1.data, res.data)
        self.assertNotIn(ser2.data, res.data)

    def test_movies_filtered_by_genre(self):
        movie1 = sample_movie(title="Avengers")
        movie2 = sample_movie(title="Pet Sematary")

        genre1 = Genre.objects.create(name="action")
        genre2 = Genre.objects.create(name="horror")

        movie1.genres.add(genre1)
        movie2.genres.add(genre2)

        movie3 = sample_movie(title="Toy Story", description="family cartoon", duration=81)

        res = self.client.get(MOVIE_URL, {"genres": f"{genre1.id},{genre2.id}"})

        ser1 = MovieListSerializer(movie1)
        ser2 = MovieListSerializer(movie2)
        ser3 = MovieListSerializer(movie3)

        self.assertIn(ser1.data, res.data)
        self.assertIn(ser2.data, res.data)
        self.assertNotIn(ser3.data, res.data)

    def test_movies_filtered_by_actors(self):

        movie1 = sample_movie(title="Avengers1")
        actor1 = Actor.objects.create(first_name="Scarlet", last_name="Johanson")
        movie1.actors.add(actor1)

        movie2 = sample_movie(title="Pet Sematary")

        movie3 = sample_movie(title="Toy Story", description="family cartoon", duration=81)

        res = self.client.get(MOVIE_URL, {"actors": f"{actor1.id}"})

        ser1 = MovieListSerializer(movie1)
        ser2 = MovieListSerializer(movie2)
        ser3 = MovieListSerializer(movie3)

        self.assertIn(ser1.data, res.data)
        self.assertNotIn(ser2.data, res.data)
        self.assertNotIn(ser3.data, res.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        movie.genres.add(Genre.objects.create(name="horror"))

        url = detail_url(movie.id)
        res = self.client.get(url)

        ser = MovieDetailSerializer(movie)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, ser.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Doctor Strange",
            "description": "Wizard",
            "duration": 115
        }

        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class MovieAdminApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "ad@ad.com",
            "tpwd",
            is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        payload = {
            "title": "Doctor Strange",
            "description": "Wizard",
            "duration": 115
        }

        res = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=res.data["id"])
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_create_movie_with_genres_and_actors(self):
        actor1 = Actor.objects.create(first_name="Scarlet", last_name="Johanson")
        genre1 = Genre.objects.create(name="action")
        genre2 = Genre.objects.create(name="horror")

        payload = {
            "title": "Doctor Strange",
            "description": "Wizard",
            "duration": 115,
            "genres": [genre1.id, genre2.id],
            "actors": [actor1.id]
        }

        res = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=res.data["id"])
        genres = movie.genres.all()
        actors = movie.actors.all()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(genres.count(), 2)
        self.assertEqual(actors.count(), 1)
        self.assertIn(genre1, genres)
        self.assertIn(genre2, genres)
        self.assertIn(actor1, actors)
