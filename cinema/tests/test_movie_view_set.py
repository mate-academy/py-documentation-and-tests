from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, Actor, Genre
from cinema.serializers import MovieListSerializer


MOVIE_URL = reverse("cinema:movie-list")


class UnauthenticatedMoviesApiTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self) -> None:
        response = self.client.get(MOVIE_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMoviesApiTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "testuser@cinema.com",
            "password1122"
        )
        self.client.force_authenticate(self.user)

    def test_movie_list(self) -> None:
        test_movie1 = Movie.objects.create(
            title="movie1",
            description="movie1 description",
            duration=100,
        )
        test_movie2 = Movie.objects.create(
            title="movie2",
            description="movie2 description",
            duration=200,
        )

        response = self.client.get(MOVIE_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)


    def test_movie_list_filter_actor(self) -> None:
        test_movie1 = Movie.objects.create(
            title="movie1",
            description="movie1 description",
            duration=100,
        )
        test_movie2 = Movie.objects.create(
            title="movie2",
            description="movie2 description",
            duration=200,
        )
        test_movie3 = Movie.objects.create(
            title="movie3",
            description="movie3 description",
            duration=300,
        )
        actor1 = Actor.objects.create(
            first_name="test name1",
            last_name="test lastname1"
        )
        actor2 = Actor.objects.create(
            first_name="test name2",
            last_name="test lastname2"
        )
        test_movie1.actors.add(actor1)
        test_movie2.actors.add(actor2)

        response = self.client.get(MOVIE_URL, {"actors": f"{actor1.id},{actor2.id}"})
        serializer1 = MovieListSerializer(test_movie1)
        serializer2 = MovieListSerializer(test_movie2)
        serializer3 = MovieListSerializer(test_movie3)

        self.assertIn(serializer1.data, response.data)
        self.assertIn(serializer2.data, response.data)
        self.assertNotIn(serializer3.data, response.data)

    def test_movie_list_filter_genre(self) -> None:
        test_movie1 = Movie.objects.create(
            title="movie1",
            description="movie1 description",
            duration=100,
        )
        test_movie2 = Movie.objects.create(
            title="movie2",
            description="movie2 description",
            duration=200,
        )
        test_movie3 = Movie.objects.create(
            title="movie3",
            description="movie3 description",
            duration=300,
        )
        genre1 = Genre.objects.create(name="testgenre1")
        genre2 = Genre.objects.create(name="testgenre2")
        test_movie1.genres.add(genre1)
        test_movie3.genres.add(genre2)

        response = self.client.get(MOVIE_URL, {"genres": f"{genre1.id},{genre2.id}"})
        serializer1 = MovieListSerializer(test_movie1)
        serializer2 = MovieListSerializer(test_movie2)
        serializer3 = MovieListSerializer(test_movie3)

        self.assertIn(serializer1.data, response.data)
        self.assertIn(serializer3.data, response.data)
        self.assertNotIn(serializer2.data, response.data)

    def test_movie_list_filter_title(self) -> None:
        test_movie1 = Movie.objects.create(
            title="movie1",
            description="movie1 description",
            duration=100,
        )
        test_movie2 = Movie.objects.create(
            title="movtitLeie2",
            description="movie2 description",
            duration=200,
        )
        test_movie3 = Movie.objects.create(
            title="TITLemovie3",
            description="movie3 description",
            duration=300,
        )
        response = self.client.get(MOVIE_URL, {"title": "title"})
        serializer1 = MovieListSerializer(test_movie1)
        serializer2 = MovieListSerializer(test_movie2)
        serializer3 = MovieListSerializer(test_movie3)

        self.assertIn(serializer2.data, response.data)
        self.assertIn(serializer3.data, response.data)
        self.assertNotIn(serializer1.data, response.data)
    
    def test_retrieve_movie_details(self) -> None:
        test_movie1 = Movie.objects.create(
            title="movie1",
            description="movie1 description",
            duration=100,
        )
        url = reverse("cinema:movie-detail", args=[test_movie1.id])
        response = self.client.get(url)

        serializer = MovieListSerializer(test_movie1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_create_movie_from_list_not_allowed(self) -> None:
        actor1 = Actor.objects.create(
            first_name="test name1",
            last_name="test lastname1"
        )
        genre1 = Genre.objects.create(name="testgenre1")
        genre2 = Genre.objects.create(name="testgenre2")
        base_info = {
            "title": "test_movie_title",
            "description": "test_movie_description",
            "duration": 100,
            "actors": [actor1.id],
            "genres": [genre1.id, genre2.id]
        }
        response = self.client.post(MOVIE_URL, base_info)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminUserMovieApiTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "testuser@cinema.com",
            "password1122",
            is_staff=True
        )
        self.client.force_authenticate(self.user)
    
    def test_create_movie_as_admin(self) -> None:
        actor1 = Actor.objects.create(
            first_name="test name1",
            last_name="test lastname1"
        )
        genre1 = Genre.objects.create(name="testgenre1")
        genre2 = Genre.objects.create(name="testgenre2")
        base_info = {
            "title": "test_movie_title",
            "description": "test_movie_description",
            "duration": 100,
            "actors": [actor1.id],
            "genres": [genre1.id, genre2.id]
        }
        response = self.client.post(MOVIE_URL, base_info)
        movie = Movie.objects.get(id=response.data["id"])
        genres = movie.genres.all()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(base_info["title"], getattr(movie, "title"))
        self.assertEqual(base_info["duration"], getattr(movie, "duration"))
        self.assertEqual(genres.count(), 2)
        self.assertIn(genre1, genres)
        self.assertIn(genre2, genres)

    def test_delete_is_forbidden(self) -> None:
        test_movie = Movie.objects.create(
            title="movie1",
            description="movie1 description",
            duration=100,
        )
        url = reverse("cinema:movie-detail", args=[test_movie.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
