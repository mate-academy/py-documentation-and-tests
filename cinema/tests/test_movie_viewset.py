from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")


def sample_movie(**params) -> Movie:
    defaults = {
        "title": "Test Movie",
        "description": "Test Movie Description",
        "duration": 60,
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=(movie_id,))


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
            email="test@test.test", password="testpassword"
        )
        self.client.force_authenticate(user=self.user)

    def test_movies_list(self):
        sample_movie()
        movie_with_genres = sample_movie(title="Movie with Genres")
        genre_1 = Genre.objects.create(name="Action")
        genre_2 = Genre.objects.create(name="Adventure")
        movie_with_genres.genres.add(genre_1, genre_2)

        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        response_data = res.data
        if isinstance(response_data, dict) and "results" in response_data:
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            self.assertEqual(response_data["results"], serializer.data)
        else:
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            self.assertEqual(response_data, serializer.data)

    def test_filter_movies_by_genres(self):
        movie_without_genres = sample_movie(title="Movie without Genres")
        movie_with_genre_1 = sample_movie(title="Action Movie")
        movie_with_genre_2 = sample_movie(title="Adventure Movie")

        genre_1 = Genre.objects.create(name="Action")
        genre_2 = Genre.objects.create(name="Adventure")

        movie_with_genre_1.genres.add(genre_1)
        movie_with_genre_2.genres.add(genre_2)

        res = self.client.get(
            MOVIE_URL,
            {"genres": f"{genre_1.id}, {genre_2.id}"},
        )

        serializer_without_genres = MovieListSerializer(movie_without_genres)
        serializer_with_genre_1 = MovieListSerializer(movie_with_genre_1)
        serializer_with_genre_2 = MovieListSerializer(movie_with_genre_2)

        response_data = res.data
        if isinstance(response_data, dict) and "results" in response_data:
            self.assertIn(serializer_with_genre_1.data,
                          response_data["results"])
            self.assertIn(serializer_with_genre_2.data,
                          response_data["results"])
            self.assertNotIn(serializer_without_genres.data,
                             response_data["results"])
        else:
            self.assertIn(serializer_with_genre_1.data, response_data)
            self.assertIn(serializer_with_genre_2.data, response_data)
            self.assertNotIn(serializer_without_genres.data, response_data)
    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        genre = Genre.objects.create(name="Action")
        actor = Actor.objects.create(
            first_name="Test",
            last_name="Actor",
        )
        movie.genres.add(genre)
        movie.actors.add(actor)

        url = detail_url(movie.id)
        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Test Movie",
            "description": "Test Movie Description",
            "duration": 60,
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@admin.test", password="testpassword", is_staff=True
        )
        self.client.force_authenticate(user=self.user)

    def test_create_movie(self):
        payload = {
            "title": "Test Movie",
            "description": "Test Movie Description",
            "duration": 60,
        }
        res = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(pk=res.data["id"])
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_upload_movie_image(self):
        movie = sample_movie()
        url = reverse("cinema:movie-upload-image", args=(movie.id,))
        with open(
            "media/uploads/movies/"
            "inception-0b8f31c7-d12d-4a76-9df0-141c131bdf4f.png",
            "rb",
        ) as image:
            res = self.client.post(url, {"image": image})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        movie.refresh_from_db()
        self.assertIn("image", res.data)

    def test_filter_movies_by_actors(self):
        actor_1 = Actor.objects.create(
            first_name="Test",
            last_name="Actor",
        )
        actor_2 = Actor.objects.create(
            first_name="Sample",
            last_name="Actor",
        )
        movie_with_actor_1 = sample_movie(title="Movie 1")
        movie_with_actor_2 = sample_movie(title="Movie 2")
        movie_with_actor_1.actors.add(actor_1)
        movie_with_actor_2.actors.add(actor_2)

        res = self.client.get(MOVIE_URL, {"actors": actor_1.id})

        serializer_with_actor_1 = MovieListSerializer(movie_with_actor_1)
        serializer_with_actor_2 = MovieListSerializer(movie_with_actor_2)

        if isinstance(res.data, list):
            self.assertIn(serializer_with_actor_1.data, res.data)
            self.assertNotIn(serializer_with_actor_2.data, res.data)
        else:
            self.assertIn(
                serializer_with_actor_1.data,
                res.data["results"])
            self.assertNotIn(
                serializer_with_actor_2.data,
                res.data["results"])

    def test_delete_movie_not_allowed(self):
        movie = sample_movie()
        url = detail_url(movie)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
