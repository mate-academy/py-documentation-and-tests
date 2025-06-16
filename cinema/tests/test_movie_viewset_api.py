from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate
from cinema.models import Genre, Actor, Movie
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")

def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])

def sample_movie(title: str, **params):
    defaults = {
        "title": title,
        "description": "Test Movie Description",
        "duration": 120,
    }

    defaults.update(params)
    return Movie.objects.create(**defaults)

def create_two_movies():
    movie_1 = sample_movie("Movie 1")
    movie_2 = sample_movie("Movie 2")

    genre_1 = Genre.objects.create(name="Drama")
    genre_2 = Genre.objects.create(name="Comedy")
    actor_1 = Actor.objects.create(first_name="Brad", last_name="Smith")
    actor_2 = Actor.objects.create(first_name="Leo", last_name="Simons")

    movie_1.genres.add(genre_1)
    movie_1.actors.add(actor_1)
    movie_2.genres.add(genre_2)
    movie_2.actors.add(actor_2)
    return movie_1, movie_2


class UnauthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.test",
            password="testpassword",
        )
        self.client.force_authenticate(self.user)

    def test_movies_list(self):
        create_two_movies()

        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movie_by_genre_or_actor_or_title(self):
        movie_1, movie_2 = create_two_movies()

        res_1_genres = self.client.get(MOVIE_URL,{"genres": 1},)
        res_2_genres = self.client.get(MOVIE_URL, {"genres": 2})

        res_1_actors = self.client.get(MOVIE_URL, {"actors": 1},)
        res_2_actors = self.client.get(MOVIE_URL, {"actors": 2})

        res_1_title = self.client.get(MOVIE_URL, {"title": "Movie 1"}, )
        res_2_title = self.client.get(MOVIE_URL, {"title": "Movie 2"}, )

        serializer_movie_1 = MovieListSerializer(
            (movie_1,),
            many=True
        )
        serializer_movie_2 = MovieListSerializer(
            (movie_2,),
            many=True
        )

        self.assertEqual(serializer_movie_1.data, res_1_genres.data)
        self.assertEqual(serializer_movie_2.data, res_2_genres.data)
        self.assertNotIn(serializer_movie_1.data, res_2_genres.data)
        self.assertNotIn(serializer_movie_2.data, res_1_genres.data)
        self.assertEqual(serializer_movie_1.data, res_1_actors.data)
        self.assertEqual(serializer_movie_2.data, res_2_actors.data)
        self.assertNotIn(serializer_movie_1.data, res_2_actors.data)
        self.assertNotIn(serializer_movie_2.data, res_1_actors.data)
        self.assertEqual(serializer_movie_1.data, res_1_title.data)
        self.assertEqual(serializer_movie_2.data, res_2_title.data)
        self.assertNotIn(serializer_movie_1.data, res_2_title.data)
        self.assertNotIn(serializer_movie_2.data, res_1_title.data)

    def test_retrieve_movie_detail(self):
        movie_1, movie_2 = create_two_movies()

        url_1 = detail_url(movie_1.id)
        url_2 = detail_url(movie_2.id)

        res_1 = self.client.get(url_1)
        res_2 = self.client.get(url_2)

        serializer_1 = MovieDetailSerializer(movie_1)
        serializer_2 = MovieDetailSerializer(movie_2)

        self.assertEqual(res_1.status_code, status.HTTP_200_OK)
        self.assertEqual(res_2.status_code, status.HTTP_200_OK)
        self.assertEqual(res_1.data, serializer_1.data)
        self.assertEqual(res_2.data, serializer_2.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Movie Test",
            "description": "Description Test",
            "duration": 123,
            "genres": 1,
            "actors": 1,
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.test",
            password="testpassword",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        genres = Genre.objects.create(name="Drama")
        actors = Actor.objects.create(first_name="Brad", last_name="Smith")

        payload = {
            "title": "Movie Test",
            "description": "Description Test",
            "duration": 123,
            "genres": (genres.id,),
            "actors": (actors.id,),
        }

        res = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=res.data["id"])
        movies = Movie.objects.all()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn(movie, movies)

    def test_delete_movie_not_allowed(self):
        movie_1, movie_2 = create_two_movies()

        url = detail_url(movie_1.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)