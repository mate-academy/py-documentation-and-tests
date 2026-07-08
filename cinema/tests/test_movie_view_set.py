from http.client import responses

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from cinema.models import Movie, Genre, Actor

MOVIE_URL = reverse("cinema:movie-list")

def detail_url(movie_id):
    return reverse("cinema:movie-detail", kwargs={"pk": movie_id})


def sample_movie(**parms):
    defaults = {
        "title": "Sample movie",
        "description": "Sample description",
        "duration": 90,
    }
    defaults.update(parms)
    return Movie.objects.create(**defaults)

class MovieViewSetTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user@test.com",
            password="Password123!",
        )
        self.admin = get_user_model().objects.create_superuser(
            email="admin@test.com",
            password="Password123!",
        )
        self.movie = sample_movie()

    def test_get_movie_list(self):
        self.client.force_authenticate(self.admin)
        sample_movie(title="Harry Potter")
        response = self.client.get(MOVIE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_get_movie_detail(self):
        self.client.force_authenticate(self.admin)
        url = detail_url(self.movie.pk)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], self.movie.title)

    def test_filter_movie_by_title(self):
        self.client.force_authenticate(self.admin)
        movie1 = sample_movie(title="Harry Potter")
        sample_movie(title="Spiderman")
        response = self.client.get(MOVIE_URL, {"title": "Harry Potter"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], movie1.title)

    def test_filter_movie_by_genre(self):
        self.client.force_authenticate(self.admin)
        genre = Genre.objects.create(name="Fantasy")
        movie = sample_movie()
        movie.genres.add(genre)
        response = self.client.get(MOVIE_URL, {"genres": genre.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_filter_movie_by_actor(self):
        self.client.force_authenticate(self.admin)
        actor = Actor.objects.create(first_name="John", last_name="Doe")
        movie = sample_movie()
        movie.actors.add(actor)
        response = self.client.get(MOVIE_URL, {"actors": actor.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_create_movie_as_admin(self):
        self.client.force_authenticate(self.admin)
        genre = Genre.objects.create(name="Fantasy")
        actor = Actor.objects.create(first_name="John", last_name="Doe")
        new_movie = {
            "title": "New Movie",
            "description": "New description",
            "duration": 90,
            "genres": [genre.id],
            "actors": [actor.id],
        }
        response = self.client.post(MOVIE_URL, new_movie)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_movie_as_user(self):
        self.client.force_authenticate(self.user)
        genre = Genre.objects.create(name="Fantasy")
        actor = Actor.objects.create(first_name="John", last_name="Doe")
        new_movie = {
            "title": "New Movie",
            "description": "New description",
            "duration": 90,
            "genres": [genre.id],
            "actors": [actor.id],
        }
        response = self.client.post(MOVIE_URL, new_movie)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_movie_without_authentication(self):
        genre = Genre.objects.create(name="Fantasy")
        actor = Actor.objects.create(first_name="John", last_name="Doe")
        new_movie = {
            "title": "New Movie",
            "description": "New description",
            "duration": 90,
            "genres": [genre.id],
            "actors": [actor.id],
        }
        response = self.client.post(MOVIE_URL, new_movie)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
