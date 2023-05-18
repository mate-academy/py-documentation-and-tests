from unittest import TestCase
from cinema.models import Movie, Actor, Genre
from cinema.serializers import MovieListSerializer, MovieDetailSerializer
from django.urls import reverse, reverse_lazy
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

MOVIE_LIST_URL = reverse_lazy("cinema:movie-list")


def sample_movie(**params):
    defaults = {
        "title": "Sample movie",
        "description": "Sample description",
        "duration": 90,
    }
    defaults.update(params)

    return Movie.objects.create(**defaults)


def get_detail_url(movie_id: int) -> reverse:
    return reverse("cinema:movie-detail", args=[movie_id])


class AnonimUserMovieTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(MOVIE_LIST_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthorizedUserMovieTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test12123123@gmail.com",
            "testpassword123"
        )
        self.client.force_authenticate(self.user)

    def test_list_movies(self):
        response = self.client.get(MOVIE_LIST_URL)

        movie = Movie.objects.all()
        serializer = MovieListSerializer(movie, many=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_movie_filter_actors(self):
        test_actor1 = Actor.objects.create(
            first_name="Jackie", last_name="Chan"
        )
        test_actor2 = Actor.objects.create(
            first_name="Jason", last_name="Statham"
        )
        movie_with_actors = sample_movie(title="Rush hour")
        movie_with_actors.actors.add(test_actor1, test_actor2)
        movie_without_actors = sample_movie(title="Mechanic")
        serializer_no_actors = MovieListSerializer(movie_without_actors)
        serializer_actors = MovieListSerializer(movie_with_actors)

        response = self.client.get(MOVIE_LIST_URL, {
            f"actors": f"{test_actor2.id},{test_actor1.id}"
                }
           )
        self.assertIn(serializer_actors.data, response.data)
        self.assertNotIn(serializer_no_actors.data, response.data)

    def test_movie_filter_genres(self):
        test_genre_1 = Genre.objects.create(name="Drama")
        test_genre_2 = Genre.objects.create(name="Poetry")
        movie_with_genre = sample_movie(title="Neo")
        movie_with_genre.genres.add(test_genre_1, test_genre_2)
        movie_without_genre = sample_movie(title="Eneyida")
        serializer_no_genre = MovieListSerializer(movie_without_genre)
        serializer_genre = MovieListSerializer(movie_with_genre)

        response = self.client.get(MOVIE_LIST_URL, {f"genres": f"{test_genre_2.id},{test_genre_1.id}"})
        self.assertIn(serializer_genre.data, response.data)
        self.assertNotIn(serializer_no_genre.data, response.data)

    def test_title_filter_genres(self):
        movie = sample_movie(title="Thriller")
        serializer_movie = MovieListSerializer(movie)

        response = self.client.get(MOVIE_LIST_URL, {f"title": f"{movie.title}"})
        self.assertIn(serializer_movie.data, response.data)

    def test_retrieve_movie(self):
        movie = sample_movie(title="Thriller")
        movie.genres.add(Genre.objects.create(name="Comedy"))
        serializer_movie = MovieDetailSerializer(movie)
        url = get_detail_url(movie.pk)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer_movie.data)

    def test_post_denied(self):
        movie_info = {
            "title": "Sample movie",
            "description": "Sample description",
            "duration": 90,
        }
        response = self.client.post(MOVIE_LIST_URL, movie_info)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def tearDown(self):
        self.user.delete()


class AdminUserMovieTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@gmail.com",
            "admin123",
            is_staff=True

        )
        self.client.force_authenticate(self.user)

    def test_post_success(self):
        movie_info = {
            "title": "Sample movie",
            "description": "Sample description",
            "duration": 90,
        }
        response = self.client.post(MOVIE_LIST_URL, movie_info)
        movie = Movie.objects.get(id=response.data["id"])
        print(movie)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        for key in movie_info:
            self.assertEqual(movie_info[key], getattr(movie, key))

    def test_post_with_actors_success(self):
        movie_info = {
            "title": "Sample movie",
            "description": "Sample description",
            "duration": 90,
        }

        test_actor1 = Actor.objects.create(
            first_name="Jackie", last_name="Chan"
        )
        test_actor2 = Actor.objects.create(
            first_name="Jason", last_name="Statham"
        )

        response = self.client.post(MOVIE_LIST_URL, movie_info)
        movie = Movie.objects.get(id=response.data["id"])
        movie.actors.add(test_actor1, test_actor2)
        self.assertEqual(movie.actors.count(), 2)
        self.assertIn(test_actor1, movie.actors.all())

    def tearDown(self):
        self.user.delete()
