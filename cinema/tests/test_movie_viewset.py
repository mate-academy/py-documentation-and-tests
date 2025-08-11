from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")


def movie_detail_url(movie_id) -> str:
    return reverse("cinema:movie-detail", args=[movie_id])


def sample_movie(**params) -> Movie:
    defaults = {
        "title": "Sample Movie",
        "duration": 100,
        "description": "Test movie"
    }
    defaults.update(**params)
    return Movie.objects.create(**defaults)


class UnAuthenticatedMovieApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self) -> None:
        response = self.client.get(MOVIE_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com",
            password="test12345"
        )
        self.client.force_authenticate(self.user)

    def test_list_movies(self) -> None:
        sample_movie()
        sample_movie()

        response = self.client.get(MOVIE_URL)
        movies = MovieListSerializer(Movie.objects.all(), many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, movies.data)

    def test_movies_filter_by_title(self) -> None:
        movie_matching = sample_movie(title="Inception")
        sample_movie(title="Interstellar")

        response = self.client.get(MOVIE_URL, {"title": "incep"})

        serializer_matching = MovieListSerializer(movie_matching)
        self.assertIn(serializer_matching.data, response.data)

    def test_movies_filter_by_genres(self) -> None:
        action_genre = Genre.objects.create(name="Action")
        drama_genre = Genre.objects.create(name="Drama")

        movie_action = sample_movie(title="Action Movie")
        movie_drama = sample_movie(title="Drama Movie")
        movie_other = sample_movie(title="Other Movie")

        movie_action.genres.add(action_genre)
        movie_drama.genres.add(drama_genre)

        response = self.client.get(MOVIE_URL, {"genres": f"{action_genre.id}"})

        serializer_action = MovieListSerializer(movie_action)
        serializer_drama = MovieListSerializer(movie_drama)
        serializer_other = MovieListSerializer(movie_other)

        self.assertIn(serializer_action.data, response.data)
        self.assertNotIn(serializer_drama.data, response.data)
        self.assertNotIn(serializer_other.data, response.data)

    def test_movies_filter_by_actors(self):
        actor_john = Actor.objects.create(first_name="John", last_name="Dow")
        actor_emma = Actor.objects.create(
            first_name="Emma",
            last_name="Watson"
        )

        movie_john = sample_movie(title="John's Movie")
        movie_emma = sample_movie(title="Emma's Movie")
        movie_other = sample_movie(title="Other Movie")

        movie_john.actors.add(actor_john)
        movie_emma.actors.add(actor_emma)

        response = self.client.get(MOVIE_URL, {"actors": f"{actor_john.id}"})

        serializer_john = MovieListSerializer(movie_john)
        serializer_emma = MovieListSerializer(movie_emma)
        serializer_other = MovieListSerializer(movie_other)

        self.assertIn(serializer_john.data, response.data)
        self.assertNotIn(serializer_emma.data, response.data)
        self.assertNotIn(serializer_other.data, response.data)

    def test_retrieve_movie_detail(self) -> None:
        movie = sample_movie(title="Inception")

        response = self.client.get(movie_detail_url(movie.id))

        serializer = MovieDetailSerializer(movie)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(serializer.data, response.data)

    def test_create_movie_forbidden(self) -> None:
        genre = Genre.objects.create(name="drama")
        actor = Actor.objects.create(first_name="Emma", last_name="Watson")
        payload = {
            "title": "Sample Movie",
            "duration": 100,
            "description": "Test movie",
            "genres": [genre.id],
            "actors": [actor.id]
        }
        response = self.client.post(MOVIE_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@admin.com",
            password="test12345",
            is_staff=1,
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self) -> None:
        genres = Genre.objects.create(name="drama")
        actor = Actor.objects.create(first_name="Emma", last_name="Watson")
        payload = {
            "title": "Sample Movie",
            "duration": 100,
            "description": "Test movie",
            "genres": [genres.id],
            "actors": [actor.id]
        }

        response = self.client.post(MOVIE_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        movie = Movie.objects.get(id=response.data["id"])
        for key in payload:
            if key == "genres":
                self.assertEqual(
                    payload[key],
                    list(getattr(movie, key).values_list("pk", flat=True))
                )
            elif key == "actors":
                self.assertEqual(
                    payload[key],
                    list(getattr(movie, key).values_list("pk", flat=True))
                )
            else:
                self.assertEqual(payload[key], getattr(movie, key))

    def test_delete_method_not_allowed(self) -> None:
        movie = sample_movie()
        url = movie_detail_url(movie.id)
        response = self.client.delete(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED
        )
