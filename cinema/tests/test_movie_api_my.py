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

    def test_upload_image_to_movie(self) -> None:
        movie = Movie.objects.create(title="Movie", description="Desc", duration=100)
        url = reverse("cinema:movie-upload-image", args=[movie.id])
        res = self.client.post(url, {"image": "data"}, format="multipart")
        self.assertNotEqual(res.status_code, status.HTTP_403_FORBIDDEN)