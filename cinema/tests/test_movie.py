from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieSerializer, MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


def sample_movie(**params):
    defaults = {
        "title": "Batman",
        "duration": 145,
        "description": "This city needs a hero..."
    }
    defaults.update(params)

    return Movie.objects.create(**defaults)


class UnauthenticatedMovieApiTests(TestCase):
    def SetUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@u.com",
            password="pastest"
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

    def test_filter_movie_by_title(self):
        sample_movie()
        sample_movie()

        res = self.client.get(MOVIE_URL, {"title": "Batman"})
        movies = Movie.objects.filter(title__icontains="Batman")
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(serializer.data, res.data)

    def test_filter_movie_by_genre(self):
        movie1 = sample_movie()
        movie2 = sample_movie()

        genre1 = Genre.objects.create(name="Biography")
        genre2 = Genre.objects.create(name="Action")

        movie1.genres.add(genre2)
        movie2.genres.add(genre1)

        movie3 = sample_movie()

        res = self.client.get(MOVIE_URL, {"genres": f"{genre1.id},{genre2.id}"})
        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie3)

        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)


    def test_movie_search_by_actors(self):
        movie1 = sample_movie()
        movie2 = sample_movie()
        movie3 = sample_movie()
        actor1 = Actor.objects.create(
            first_name="Benedict",
            last_name="Cumberbatch"
        )
        actor2 = Actor.objects.create(
            first_name="Nickolas",
            last_name="Cage"
        )
        movie1.actors.add(actor1)
        movie2.actors.add(actor2)

        res = self.client.get(MOVIE_URL, {"actors": f"{actor1.id},{actor2.id}"})
        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie3)

        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        movie.genres.add(Genre.objects.create(name="Thriller"))

        url = detail_url(movie.id)

        response = self.client.get(url)
        serializer = MovieDetailSerializer(movie)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(serializer.data, response.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Superman",
            "duration": 156
        }

        response = self.client.post(MOVIE_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@u.com",
            password="pastest",
            is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_movie_success(self):
        payload = {
            "title": "Superman",
            "duration": 156,
            "description": "We nee a hero",
        }

        response = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=response.data["id"])

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_create_movie_with_genre_and_actor(self):
        genre = Genre.objects.create(name="Action")
        actor = Actor.objects.create(
            first_name="Benedict",
            last_name="Cumberbatch"
        )

        payload = {
            "title": "Superman",
            "duration": 156,
            "description": "We nee a hero",
            "genres": genre.id,
            "actors": actor.id,
        }

        response = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=response.data["id"])
        genres = movie.genres.all()
        actors = movie.actors.all()

        self.assertEqual(genres.count(), 1)
        self.assertEqual(actors.count(), 1)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_deletion_not_allowed(self):
        movie = sample_movie()

        url = detail_url(movie.id)

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


    def test_update_not_allowed(self):
        movie = sample_movie()
        payload = {
            "title": "Ringo",
            "description": "Helllooo",
            "duration": 123,
        }
        res = self.client.patch(detail_url(movie.id), payload)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
