import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient, APITestCase
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cinema.settings')
django.setup()

MOVIES_URL = reverse("cinema:movie-list")
MOVIE_SESSION_URL = reverse("cinema:moviesession-list")


def sample_movie(**params):
    defaults = {
        "title": "Sample movie",
        "description": "Sample description",
        "duration": 90,
    }
    defaults.update(params)

    return Movie.objects.create(**defaults)


def sample_genre(**params):
    defaults = {
        "name": "Drama",
    }
    defaults.update(params)

    return Genre.objects.create(**defaults)


def sample_actor(**params):
    defaults = {"first_name": "George", "last_name": "Clooney"}
    defaults.update(params)

    return Actor.objects.create(**defaults)


def sample_movie_session(**params):
    cinema_hall = CinemaHall.objects.create(
        name="Blue", rows=20, seats_in_row=20
    )

    defaults = {
        "show_time": "2022-06-02 14:00:00",
        "movie": None,
        "cinema_hall": cinema_hall,
    }
    defaults.update(params)

    return MovieSession.objects.create(**defaults)


def image_upload_url(movie_id):
    """Return URL for recipe image upload"""
    return reverse("cinema:movie-upload-image", args=[movie_id])


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


class MovieViewSetTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            "user@example.com", "testpass123"
        )
        self.client.force_authenticate(self.user)

        self.genre1 = sample_genre(name="Action")
        self.genre2 = sample_genre(name="Comedy")

        self.actor1 = sample_actor(first_name="Tom", last_name="Hanks")
        self.actor2 = sample_actor(first_name="Will", last_name="Smith")

        self.movie1 = Movie.objects.create(
            title="Avengers", description="Superheroes save the world", duration=143
        )
        self.movie1.genres.add(self.genre1)
        self.movie1.actors.add(self.actor1)

        self.movie2 = Movie.objects.create(
            title="Bad Boys", description="Detectives in Miami", duration=120
        )
        self.movie2.genres.add(self.genre2)
        self.movie2.actors.add(self.actor2)

    def test_list_movies(self):
        res = self.client.get(MOVIES_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)

    def test_filter_movies_by_title(self):
        res = self.client.get(MOVIES_URL, {"title": "Avengers"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data[0]["title"], "Avengers")
        self.assertEqual(len(res.data), 1)

    def test_filter_by_genres(self):
        res = self.client.get(MOVIES_URL, {"genres": f"{self.genre1.id}"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data[0]["title"], self.movie1.title)
        self.assertEqual(len(res.data), 1)

    def test_filter_by_actors(self):
        res = self.client.get(MOVIES_URL, {"actors": f"{self.actor2.id}"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data[0]["title"], self.movie2.title)
        self.assertEqual(len(res.data), 1)

    def test_movie_detail(self):
        url = reverse("cinema:movie-detail", args=[self.movie1.id])
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["title"], self.movie1.title)

    def test_unauthenticated_user_cannot_access_list(self):
        self.client.force_authenticate(user=None)
        res = self.client.get(MOVIES_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
