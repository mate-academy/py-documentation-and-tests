from django.contrib.auth import get_user_model
from django.test import TestCase

from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from cinema.models import MovieSession, Movie, CinemaHall, Actor, Genre
from cinema.serializers import (
    MovieSessionListSerializer,
    MovieSessionDetailSerializer
)


MOVIE_SESSION_URL = reverse("cinema:moviesession-list")

def sample_movie_session(**params):
    actor = Actor.objects.create(first_name="John", last_name="Doe")
    genre = Genre.objects.create(name="Fantasy")

    movie = Movie.objects.create(
        title="test_movie_title",
        description="test_movie_description",
        duration=100,
    )
    movie.genres.add(genre)
    movie.actors.add(actor)
    cinema_hall = CinemaHall.objects.create(
        name="test_cinema_hall_name",
        rows=5,
        seats_in_row=10
    )
    defaults = {
        "show_time": "2026-04-22",
        "movie": movie,
        "cinema_hall": cinema_hall,
    }
    defaults.update(params)
    return MovieSession.objects.create(**defaults)

def detail_url(movie_session_id):
    return reverse("cinema:movie-session-detail", args=[movie_session_id])


class UnauthenticatedMovieSessionApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_SESSION_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
