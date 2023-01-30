from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase
from rest_framework import status

from cinema.models import Movie, Genre, Actor
from rest_framework.test import APIClient

from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")


def create_movie(**params):
    defaults = {
        "title": "test title",
        "description": "test description",
        "duration": 145,

    }
    defaults.update(params)
    return Movie.objects.create(**defaults)


def detail_url(movie_id: int):
    return reverse("cinema:movie-detail", args=[movie_id])


class UnauthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assert_(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@test.com",
            "testpass",
        )
        self.client.force_authenticate(self.user)

    def test_movie_list(self):
        create_movie()
        movie_with_genre_actor = create_movie()

        genre = Genre.objects.create(name="drama")
        actor = Actor.objects.create(
            first_name="alex",
            last_name="bouldwin"
        )

        movie_with_genre_actor.genres.add(genre)
        movie_with_genre_actor.actors.add(actor)
        res = self.client.get(MOVIE_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movie_by_title_genre(self):
        movie1 = create_movie(title="hello")
        movie2 = create_movie(title="world")

        genre = Genre.objects.create(name="drama")

        movie1.genres.add(genre)
        movie2.genres.add(genre)

        res = self.client.get(MOVIE_URL, {"genres": f"{genre.id}"})

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)

        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)

    def test_retrieve_movie_detail(self):
        movie = create_movie()
        movie.genres.add(Genre.objects.create(name="drama"))
        movie.actors.add(Actor.objects.create(
            first_name="matt",
            last_name="daimond"
        ))

        url = detail_url(movie.id)
        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "test",
            "description": "test desc",
            "duration": 1555
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminBusApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@test.com",
            "testpass",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)

    def test_creat_movie(self):
        actor = Actor.objects.create(
            first_name="bruce",
            last_name="lee"
        )
        genre = Genre.objects.create(name="fighters")

        payload = {
            "title": "test title",
            "description": "test description",
            "duration": 155,
            "actors": actor.id,
            "genres": genre.id,
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
