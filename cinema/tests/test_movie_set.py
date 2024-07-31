from cinema.models import Actor, Genre, Movie
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

from django.contrib.auth import get_user_model
from django.contrib.sites import requests
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

url = reverse("cinema:movie-list")


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])

def create_movie(data) -> Movie:
    return Movie.objects.create(**data)


class TestPermissionForMovieSet(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_anonymous_user(self):
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_user(self):
        user = get_user_model().objects.create_user(
            email="test@gmail.com",
            password="test123",
        )
        self.client.force_authenticate(user=user)
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        res2 = self.client.post(url)
        self.assertEqual(res2.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_user(self):
        user = get_user_model().objects.create_superuser(
            email="admin@gmail.com",
            password="admin123",
        )
        self.client.force_authenticate(user=user)
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        actor = Actor.objects.create(first_name="John", last_name="Doe")
        genre = Genre.objects.create(name="Fantasy")
        data = {
            "title": "Example Movie",
            "description": "An example movie description",
            "duration": 120,
            "genres": [genre.id],
            "actors": [actor.id],
        }
        res2 = self.client.post(url, data, format="json")
        self.assertEqual(res2.status_code, status.HTTP_201_CREATED)
        movie_for_delete = create_movie({
            "title": "movie-test",
            "description": "test-movie",
            "duration": 200,
        })

        res = self.client.delete(url)
        self.assertEqual(res.status_code, 405)


class TestMovieSet(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@gmail.com",
            password="test123",
        )
        self.client.force_authenticate(user=self.user)
        self.genre1 = Genre.objects.create(name="Fantasy")
        self.genre2 = Genre.objects.create(name="Si-fi")
        self.genre3 = Genre.objects.create(name="horror")
        self.actor1 = Actor.objects.create(first_name="John", last_name="Doe")
        self.actor2 = Actor.objects.create(first_name="Jack", last_name="Smith")
        self.actor3 = Actor.objects.create(first_name="Will", last_name="Smith")
        self.movie1 = create_movie({
            "title": "movie1",
            "description": "first movie",
            "duration": 120,
        })
        self.movie2 = create_movie({
            "title": "movie2",
            "description": "second movie",
            "duration": 150,
        })
        self.movie3 = create_movie({
            "title": "movie3",
            "description": "third movie",
            "duration": 180,
        })

    def test_queryset(self):
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 3)

    def test_filter_queryset(self):
        self.movie1.genres.add(self.genre1, self.genre2)
        self.movie1.actors.add(self.actor1, self.actor2)

        self.movie2.genres.add(self.genre2, self.genre3)
        self.movie2.actors.add(self.actor2, self.actor3)

        self.movie3.genres.add(self.genre1, self.genre3)
        self.movie3.actors.add(self.actor1, self.actor3)

        res = self.client.get(url, {"genres": self.genre1.id})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)

        res2 = self.client.get(url, {"genres": self.genre2.id,
                                     "actors": self.actor1.id})
        self.assertEqual(len(res2.data), 1)

        res3 = self.client.get(url, {"genres": self.genre3.id})
        serializer_movie1 = MovieListSerializer(self.movie1)
        serializer_movie2 = MovieListSerializer(self.movie2)
        serializer_movie3 = MovieListSerializer(self.movie3)
        self.assertNotIn(serializer_movie1.data, res3.data)
        self.assertIn(serializer_movie2.data, res3.data)
        self.assertIn(serializer_movie3.data, res3.data)

    def test_retrieve_movie_detail(self):
        movie = self.movie1
        movie.genres.add(self.genre1, self.genre2)
        movie.actors.add(self.actor1, self.actor2)

        url = detail_url(movie.id)
        res = self.client.get(url)
        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)
