from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")

def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])

class UnauthenticatedMovieApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self) -> None:
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

class AuthenticatedMovieApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "user@test.com", "password123"
        )
        self.client.force_authenticate(self.user)

        self.genre = Genre.objects.create(name="Drama")
        self.actor = Actor.objects.create(first_name="John", last_name="Doe")
        self.movie = Movie.objects.create(
            title="Test Movie",
            description="Description",
            duration=120
        )
        self.movie.genres.add(self.genre)
        self.movie.actors.add(self.actor)

    def test_list_movies(self) -> None:
        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_title(self) -> None:
        movie_target = Movie.objects.create(
            title="Avatar",
            description="Blue",
            duration=160
        )
        res = self.client.get(MOVIE_URL, {"title": "avatar"})
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], movie_target.title)

    def test_filter_movies_by_genres(self):
        genre1 = Genre.objects.create(name="Action-genre")
        genre2 = Genre.objects.create(name="Drama-genre")

        movie1 = Movie.objects.create(
            title="Action movie",
            description="Desc",
            duration=100,
        )
        movie2 = Movie.objects.create(
            title="Drama movie",
            description="Desc",
            duration=100,
        )

        movie1.genres.add(genre1)
        movie2.genres.add(genre2)

        res = self.client.get(
            MOVIE_URL,
            {"genres": str(genre1.id)}
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["id"], movie1.id)

    def test_filter_movies_by_actors(self):
        actor1 = Actor.objects.create(
            first_name="Tom",
            last_name="Hardy"
        )
        actor2 = Actor.objects.create(
            first_name="Brad",
            last_name="Pitt"
        )

        movie1 = Movie.objects.create(
            title="Movie with Tom",
            description="Desc",
            duration=100,
        )
        movie2 = Movie.objects.create(
            title="Movie with Brad",
            description="Desc",
            duration=100,
        )

        movie1.actors.add(actor1)
        movie2.actors.add(actor2)

        res = self.client.get(
            MOVIE_URL,
            {"actors": str(actor1.id)}
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["id"], movie1.id)

    def test_retrieve_movie_detail(self) -> None:
        url = detail_url(self.movie.id)
        res = self.client.get(url)
        serializer = MovieDetailSerializer(self.movie)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self) -> None:
        payload = {"title": "Forbidden", "description": "Desc", "duration": 100}
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_regular_user_forbidden_upload_image(self):
        user = get_user_model().objects.create_user(
            email="usertest@test.com",
            password="password"
        )
        self.client.force_authenticate(user)

        movie = Movie.objects.create(
            title="Movie",
            description="Desc",
            duration=100,
        )

        url = reverse("cinema:movie-upload-image", args=[movie.id])
        res = self.client.post(
            url,
            {"image": "data"},
            format="multipart"
        )

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

class AdminMovieApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@test.com", "admin123"
        )
        self.client.force_authenticate(self.user)
        self.genre = Genre.objects.create(name="Action")
        self.actor = Actor.objects.create(first_name="Jack", last_name="Black")

    def test_create_movie(self) -> None:
        payload = {
            "title": "New Movie",
            "description": "Cool movie",
            "duration": 150,
            "genres": [self.genre.id],
            "actors": [self.actor.id]
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_upload_image_with_invalid_data_bad_request(self) -> None:
        movie = Movie.objects.create(title="Movie", description="Desc", duration=100)
        url = reverse("cinema:movie-upload-image", args=[movie.id])
        res = self.client.post(url, {"image": "data"}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)