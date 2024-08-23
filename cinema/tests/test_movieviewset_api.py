from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.urls import reverse
from django.contrib.auth import get_user_model

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


def test_movie(**params) -> Movie:
    default_movie = {
        "title": "test_movie_title",
        "description": "test_movie_description",
        "duration": 10,
    }
    default_movie.update(params)

    return Movie.objects.create(**default_movie)


class UnauthenticatedMovieApiTest(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class АuthenticatedMovieApiTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test_user@email.com",
            password="test_user",
        )
        self.client.force_authenticate(user=self.user)

    def test_movie_list(self):
        test_movie()

        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_movies_filter_genres(self):

        movie_without_genres = test_movie()
        movie_with_genres_1_2 = test_movie()
        movie_with_genres_1 = test_movie()

        test_genre_1 = Genre.objects.create(name="test_genre_1")
        test_genre_2 = Genre.objects.create(name="test_genre_2")

        movie_with_genres_1_2.genres.set([test_genre_1, test_genre_2])
        movie_with_genres_1_2.save()

        movie_with_genres_1.genres.set([test_genre_1])
        movie_with_genres_1.save()

        res = self.client.get(
            MOVIE_URL,
            {"genres": f"{test_genre_1.id},{test_genre_2.id}"}
        )
        serializer_without_genres = MovieListSerializer(movie_without_genres)
        serializer_with_genres_1_2 = MovieListSerializer(movie_with_genres_1_2)
        serializer_with_genres_1 = MovieListSerializer(movie_with_genres_1)

        self.assertIn(serializer_with_genres_1.data, res.data)
        self.assertIn(serializer_with_genres_1_2.data, res.data)
        self.assertNotIn(serializer_without_genres.data, res.data)

    def test_movies_filter_actors(self):

        movie_without_actors = test_movie()
        movie_with_actors_1_2 = test_movie()
        movie_with_actors_1 = test_movie()

        test_actor_1 = Actor.objects.create(first_name="test_actor_1", last_name="test")
        test_actor_2 = Actor.objects.create(first_name="test_actor_2", last_name="test")

        movie_with_actors_1_2.actors.set([test_actor_1, test_actor_2])
        movie_with_actors_1_2.save()

        movie_with_actors_1.actors.set([test_actor_1])
        movie_with_actors_1.save()

        res = self.client.get(
            MOVIE_URL,
            {"actors": f"{test_actor_1.id},{test_actor_2.id}"}
        )
        serializer_without_actors = MovieListSerializer(movie_without_actors)
        serializer_with_actors_1_2 = MovieListSerializer(movie_with_actors_1_2)
        serializer_with_actors_1 = MovieListSerializer(movie_with_actors_1)

        self.assertIn(serializer_with_actors_1.data, res.data)
        self.assertIn(serializer_with_actors_1_2.data, res.data)
        self.assertNotIn(serializer_without_actors.data, res.data)

    def test_movies_filter_title(self):

        movie_title = test_movie()
        movie_title_1 = test_movie(title="test_movie_title_1")

        res = self.client.get(
            MOVIE_URL,
            {"title": "le_1"}
        )
        serializer_with_title = MovieListSerializer(movie_title)
        serializer_with_with_title_1 = MovieListSerializer(movie_title_1)

        self.assertIn(serializer_with_with_title_1.data, res.data)
        self.assertNotIn(serializer_with_title.data, res.data)

    def test_retrieve_movie_detail(self):
        movie = test_movie()

        url = detail_url(movie.id)

        res = self.client.get(url)
        serializer = MovieDetailSerializer(movie)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "test_movie_title",
            "description": "test_movie_description",
            "duration": 10,
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin_user@email.com",
            password="admin_user",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.user)

    def test_create_movie(self):
        payload = {
            "title": "test_movie_title",
            "description": "test_movie_description",
            "duration": 10,
        }
        res = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_create_movie_with_genres_and_actors(self):

        test_genre_1 = Genre.objects.create(name="test_genre_1")
        test_genre_2 = Genre.objects.create(name="test_genre_2")
        test_actor_1 = Actor.objects.create(first_name="test_actor_1", last_name="test")
        test_actor_2 = Actor.objects.create(first_name="test_actor_2", last_name="test")

        payload = {
            "title": "test_movie_title",
            "description": "test_movie_description",
            "duration": 10,
            "genres": [test_genre_1.id, test_genre_2.id],
            "actors": [test_actor_1.id, test_actor_2.id],
        }

        res = self.client.post(
            MOVIE_URL,
            payload
        )
        movie = Movie.objects.get(id=res.data["id"])

        genres = movie.genres.all()
        actors = movie.actors.all()

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn(test_genre_1, genres)
        self.assertIn(test_genre_2, genres)
        self.assertEqual(genres.count(), 2)
        self.assertIn(test_actor_1, actors)
        self.assertIn(test_actor_2, actors)
        self.assertEqual(actors.count(), 2)

    def test_upload_image_to_movie(self):
        movie = test_movie()
        url = reverse("cinema:movie-upload-image", args=[movie.id])
        with open("media/test_image.jpg", "rb") as image:
            res = self.client.post(url, {"image": image}, format="multipart")

        movie.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(movie.image)
