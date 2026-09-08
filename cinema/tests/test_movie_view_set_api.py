from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse

from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer

MOVIE_URL = reverse("cinema:movie-list")


def sample_movie(**params) -> Movie:
    defaults = {
        "title": "Prof",
        "description": "Test Movie",
        "duration": 12,
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)


class UnaAuthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com", password="testpassword"
        )
        self.client.force_authenticate(self.user)

    def test_movies_list(self):
        sample_movie()

        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.data, serializer.data)

    def test_get_movie_by_id(self):
        mv = sample_movie()
        MOVIE_DETAIL_URL = reverse("cinema:movie-detail", [mv.id])

        res = self.client.get(MOVIE_DETAIL_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], mv.id)
        self.assertEqual(res.data["title"], mv.title)

    def test_filter_movie_by_title(self):
        movie_with_title = sample_movie()
        movie_with_another_title = sample_movie(title="Looper")

        res = self.client.get(MOVIE_URL, {"title": "pro"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["id"], movie_with_title.id)

    def test_filter_movie_by_genres(self):
        movie_with_genre = Movie.objects.create(
            title="Prof", description="Test Movie", duration=12
        )
        movie_without_genre = sample_movie()

        genre_1 = Genre.objects.create(name="Mystery")

        movie_with_genre.genres.add(genre_1)

        res = self.client.get(MOVIE_URL, {"genres": genre_1.id})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["id"], movie_with_genre.id)

    def test_filter_movie_by_actors(self):
        movie_with_actor = Movie.objects.create(
            title="Prof", description="Test Movie", duration=12
        )
        movie_without_actor = sample_movie()

        actor_1 = Actor.objects.create(first_name="Matt", last_name="Damon")

        movie_with_actor.actors.add(actor_1)

        res = self.client.get(MOVIE_URL, {"actors": actor_1.id})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["id"], movie_with_actor.id)

    def test_authenticated_user_create_movie(self):
        res = self.client.post(
            MOVIE_URL, {"title": "Prof", "description": "Test Movie", "duration": 12}
        )

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_request_movie_by_nonexistent_id(self):
        MOVIE_DETAIL_URL = reverse("cinema:movie-detail", [100])

        res = self.client.get(MOVIE_DETAIL_URL)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_authenticated_user_cannot_upload_image(self):
        movie = sample_movie()
        MOVIE_DETAIL_ACTION = reverse("cinema:movie-upload-image", [movie.id])

        res = self.client.post(MOVIE_DETAIL_ACTION, {})

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            email="admin@test.com", password="testpassword"
        )
        self.client.force_authenticate(self.user)

        self.genre = Genre.objects.create(name="Mystery")
        self.actor = Actor.objects.create(first_name="Leonardo", last_name="DiCaprio")

    def test_superuser_create_movie(self):
        res = self.client.post(
            MOVIE_URL,
            {
                "title": "Prof",
                "description": "Test Movie",
                "duration": 12,
                "genres": [self.genre.id],
                "actors": [self.actor.id],
            },
        )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
