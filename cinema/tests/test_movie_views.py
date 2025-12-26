import tempfile

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from cinema.models import Movie, Actor, Genre
from cinema.serializers import (
    MovieListSerializer,
    MovieDetailSerializer,
)

URL = reverse("cinema:movie-list")


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


def create_movie(**params) -> Movie:
    defaults = {
        "title": "Test",
        "description": "Test",
        "duration": 10,
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)


def create_actor(**params) -> Actor:
    defaults = {
        "first_name": "Test",
        "last_name": "Test",
    }
    defaults.update(params)
    return Actor.objects.create(**defaults)


def create_genre(**params) -> Genre:
    defaults = {
        "name": "Test",
    }
    defaults.update(params)
    return Genre.objects.create(**defaults)


class UnauthenticatedUser(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedUser(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.test",
            password="testtest",
        )
        self.client.force_authenticate(self.user)

    def test_movie_list(self):
        create_movie()
        res = self.client.get(URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)
        self.assertEqual(res.data, serializer.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_movie_filter(self):
        movie_1 = create_movie(title="Test1")
        movie_2 = create_movie(title="Test2")
        movie_3 = create_movie(title="Test3")

        actor_1 = create_actor(first_name="Test1")
        actor_2 = create_actor(first_name="Test2")
        actor_3 = create_actor(first_name="Test3")
        genre_1 = create_genre(name="Test1")
        genre_2 = create_genre(name="Test2")
        genre_3 = create_genre(name="Test3")

        movie_1.actors.add(actor_1)
        movie_1.genres.add(genre_1)

        movie_2.actors.add(actor_2)
        movie_2.genres.add(genre_2)

        movie_3.actors.add(actor_3)
        movie_3.genres.add(genre_3)

        res_1 = self.client.get(
            URL,
            {
                "title": "Test1",
            },
        )
        res_2 = self.client.get(
            URL,
            {
                "genres": f"{genre_2.id}",
            },
        )
        res_3 = self.client.get(
            URL,
            {
                "actors": f"{actor_3.id}",
            },
        )

        serializer_1 = MovieListSerializer(movie_1)
        serializer_2 = MovieListSerializer(movie_2)
        serializer_3 = MovieListSerializer(movie_3)

        self.assertIn(serializer_1.data, res_1.data)
        self.assertIn(serializer_2.data, res_2.data)
        self.assertIn(serializer_3.data, res_3.data)
        self.assertNotIn(serializer_1.data, res_2.data)
        self.assertNotIn(serializer_2.data, res_3.data)
        self.assertNotIn(serializer_3.data, res_1.data)

    def test_retrieve_movie(self):
        movie = create_movie()
        actor = create_actor()
        genre = create_genre()

        movie.actors.add(actor)
        movie.genres.add(genre)

        url = detail_url(movie.id)
        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Test",
            "description": "Test",
            "duration": 10,
        }

        res = self.client.post(URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@admin.admin",
            password="adminadmin",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        actor = create_actor()
        genre = create_genre()
        payload = {
            "title": "Test",
            "description": "Test",
            "duration": 10,
            "genres": [genre.id],
            "actors": [actor.id],
        }

        res = self.client.post(URL, payload)

        movie = Movie.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        self.assertEqual(payload["title"], movie.title)
        self.assertEqual(payload["description"], movie.description)
        self.assertEqual(payload["duration"], movie.duration)
        self.assertEqual(
            payload["genres"], list(movie.genres.values_list("id", flat=True))
        )
        self.assertEqual(
            payload["actors"], list(movie.actors.values_list("id", flat=True))
        )

    def test_upload_image(self):
        movie = create_movie()
        url = reverse("cinema:movie-upload-image", args=[movie.id])

        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            response = self.client.post(url, {"image": ntf}, format="multipart")

        movie.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(bool(movie.image))
