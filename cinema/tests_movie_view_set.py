from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.reverse import reverse
from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import Movie, Actor, Genre
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_LIST_URL = reverse("cinema:movie-list")


def sample_movie(**params) -> Movie:
    defaults = {
        "title": "Test Title",
        "description": "Test description",
        "duration": 120
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)


def sample_actor(**params):
    defaults = {
        "first_name": "John",
        "last_name": "Cena"
    }
    defaults.update(params)
    return Actor.objects.create(**defaults)


def sample_genre(**params):
    defaults = {
        "name": "Test",
    }
    defaults.update(params)
    return Genre.objects.create(**defaults)


class UnauthenticatedTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(MOVIE_LIST_URL)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED
        )


class AuthenticatedTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user@example.com",
            password="user_password"
        )
        self.client.force_authenticate(self.user)

    def test_get_movie_list(self):
        sample_movie()
        response = self.client.get(MOVIE_LIST_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(
            response.data,
            serializer.data
        )

    def test_get_movie_retrieve(self):
        new_movie = sample_movie()
        response = self.client.get(reverse(
            "cinema:movie-detail",
            kwargs={"pk": new_movie.pk}
        ))
        serializer = MovieDetailSerializer(new_movie)
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )
        self.assertEqual(
            response.data,
            serializer.data
        )

    def test_post_movie_forbidden(self):
        response = self.client.post(
            MOVIE_LIST_URL,
            {
                "title": "Test Title",
                "description": "Test description",
                "duration": 120
            }
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN
        )

    def get_movie_response(self, **params):
        return self.client.get(MOVIE_LIST_URL, params)

    def assert_movie_in_response(self, movie, response):
        serializer = MovieListSerializer(movie)
        self.assertIn(serializer.data, response.data)

    def assert_movie_not_in_response(self, movie, response):
        serializer = MovieListSerializer(movie)
        self.assertNotIn(serializer.data, response.data)

    def test_filter_movies_by_title(self):
        first_movie = sample_movie(title="Title 1")
        second_movie = sample_movie(title="Title 2")

        first_response = self.get_movie_response(title="1")
        second_response = self.get_movie_response(title="2")
        third_response = self.get_movie_response(title="Title")

        self.assert_movie_in_response(first_movie, first_response)
        self.assert_movie_in_response(second_movie, second_response)

        self.assert_movie_not_in_response(first_movie, second_response)
        self.assert_movie_not_in_response(second_movie, first_response)

        combined_serializer = MovieListSerializer(
            [first_movie, second_movie],
            many=True
        )
        self.assertEqual(third_response.data, combined_serializer.data)

    def test_filter_movies_by_genres_id(self):
        action_movie = sample_movie(title="Action Movie")
        drama_movie = sample_movie(title="Drama Movie")

        action = sample_genre(name="Genre")
        drama = sample_genre(name="Drama")

        action_movie.genres.add(action)
        drama_movie.genres.add(drama)

        first_response = self.get_movie_response(genres=f"{action.pk}")
        second_response = self.get_movie_response(genres=f"{drama.pk}")
        third_response = self.get_movie_response(
            genres=f"{action.pk},{drama.pk}"
        )

        self.assert_movie_in_response(action_movie, first_response)
        self.assert_movie_in_response(drama_movie, second_response)

        self.assert_movie_not_in_response(drama_movie, first_response)
        self.assert_movie_not_in_response(action_movie, second_response)

        combined_serializer = MovieListSerializer(
            [action_movie, drama_movie],
            many=True
        )
        self.assertEqual(combined_serializer.data, third_response.data)

    def test_filter_movies_by_actors(self):
        movie_with_leonardo = sample_movie(title="Movie with DiCaprio")
        movie_with_john = sample_movie(title="Movie with Cena")

        leonardo_dicaprio = sample_actor(
            first_name="Leonardo", last_name="DiCaprio"
        )
        john_cena = sample_actor()

        movie_with_leonardo.actors.add(leonardo_dicaprio)
        movie_with_john.actors.add(john_cena)

        first_response = self.get_movie_response(
            actors=f"{leonardo_dicaprio.pk}"
        )
        second_response = self.get_movie_response(
            actors=f"{john_cena.pk}"
        )
        third_response = self.get_movie_response(
            actors=f"{leonardo_dicaprio.pk},{john_cena.pk}"
        )

        self.assert_movie_in_response(movie_with_leonardo, first_response)
        self.assert_movie_in_response(movie_with_john, second_response)

        self.assert_movie_not_in_response(movie_with_leonardo, second_response)
        self.assert_movie_not_in_response(movie_with_john, first_response)

        combined_serializer = MovieListSerializer(
            [movie_with_john, movie_with_leonardo],
            many=True
        )
        print("response_data:", third_response.data)
        print("serializer_data:", combined_serializer.data)
        self.assertEqual(third_response.data, combined_serializer.data)
