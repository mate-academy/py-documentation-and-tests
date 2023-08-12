from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")


def sample_movie(**params):
    defaults = {
        "title": "TestTitle",
        "description": "TestDes",
        "duration": 100
    }
    defaults.update(**params)
    return Movie.objects.create(**defaults)


def detail_url(movie_id: int):
    return reverse("cinema:movie-detail", args=[movie_id])


class UnauthenticatedMovieApiTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(MOVIE_URL)

        self.assertEquals(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTest(TestCase):

    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@test.com",
            "testpass",
        )
        self.client.force_authenticate(self.user)

    def test_list_movie(self):
        sample_movie()
        movies_with_genres_and_actors = sample_movie()

        genre = Genre.objects.create(name="testgenre")
        actor = Actor.objects.create(
            first_name="NameTest",
            last_name="SurnameTest"
        )
        movies_with_genres_and_actors.actors.add(actor)
        movies_with_genres_and_actors.genres.add(genre)

        response = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data, serializer.data)

    def test_filter_movies_by_genres_and_actors_and_title(self):
        movie1 = sample_movie(title="Movie 1")
        movie2 = sample_movie(title="Movie 2")

        genre1 = Genre.objects.create(name="testgenre1")
        genre2 = Genre.objects.create(name="testgenre2")

        actor1 = Actor.objects.create(
            first_name="TestName1",
            last_name="TestSurname1"
        )
        actor2 = Actor.objects.create(
            first_name="TestName2",
            last_name="TestSurname2"
        )

        movie1.genres.add(genre1)
        movie2.genres.add(genre2)

        movie1.actors.add(actor1)
        movie2.actors.add(actor2)

        movie3 = sample_movie(title="Movie with out genres")

        response1 = self.client.get(
            MOVIE_URL,
            {"genres": f"{genre1.id},{genre2.id}"}
        )

        response2 = self.client.get(
            MOVIE_URL,
            {"actors": f"{actor1.id}, {actor2.id}"}
        )

        response3 = self.client.get(
            MOVIE_URL,
            {"title": "1"}
        )

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie3)

        self.assertIn(serializer1.data, response1.data)
        self.assertIn(serializer2.data, response1.data)
        self.assertNotIn(serializer3.data, response1.data)

        self.assertIn(serializer1.data, response2.data)
        self.assertIn(serializer2.data, response2.data)
        self.assertNotIn(serializer3.data, response2.data)

        self.assertIn(serializer1.data, response3.data)

    def test_movie_retrieve(self):
        movie = sample_movie(title="MovieTest")
        url = detail_url(movie.id)

        response = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(serializer.data, response.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "MovieTest",
            "description": "TestDes",
            "duration": 22
        }

        response = self.client.post(MOVIE_URL, payload)

        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@test.com",
            "testpass",
            is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_movie_with_actors_genres(self):
        genre = Genre.objects.create(name="TestGenre")
        actor = Actor.objects.create(
            first_name="TestName",
            last_name="TestSurname"
        )
        payload = {
            "title": "MovieTest",
            "description": "TestDes",
            "duration": 22,
            "actors": [actor.id, ],
            "genres": [genre.id, ],
        }
        response = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=response.data["id"])

        genres = movie.genres.all()
        actors = movie.actors.all()

        self.assertEquals(response.status_code, status.HTTP_201_CREATED)

        self.assertEquals(genres.count(), 1)
        self.assertEquals(actors.count(), 1)
        self.assertIn(genre, genres)
        self.assertIn(actor, actors)

    def test_create_movie_without_actors_genres(self):
        payload = {
            "title": "MovieTest",
            "description": "TestDes",
            "duration": 22,
        }

        response = self.client.post(MOVIE_URL, payload)

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_movie(self):
        payload = {
            "title": "MovieTest2",
            "duration": 22
        }

        genre = Genre.objects.create(name="TestGenre")
        actor = Actor.objects.create(
            first_name="TestName",
            last_name="TestSurname"
        )

        movie = sample_movie(title="MovieTest1")

        movie.actors.add(actor)
        movie.genres.add(genre)

        url = detail_url(movie.id)

        response = self.client.patch(url, payload)

        self.assertEquals(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
