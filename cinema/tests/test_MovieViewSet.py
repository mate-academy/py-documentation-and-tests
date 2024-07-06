from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer
from user.models import User


suffix = 0


def create_genre(suffix):
    Genre.objects.create(name=f"Test genre{suffix}")


def create_actor(suffix):
    Actor.objects.create(
        first_name=f"Actorname{suffix}", last_name=f"Actor LastName{suffix}"
    )


def create_movie(suffix=None, genres: list = None, actors: list = None):

    data = {
        "title": f"Title{suffix}",
        "description": "description",
        "duration": 109,
    }

    movie = Movie.objects.create(**data)

    if actors:
        movie.actors.set(actors)
    if genres:
        movie.genres.set(genres)
    return movie


class MovieViewSetTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.url = reverse("cinema:movie-list")

    def test_anon_user_no_access(self):
        response_list = self.client.get(self.url)
        self.assertEqual(
            response_list.status_code, status.HTTP_401_UNAUTHORIZED
        )

        response_create = self.client.post(
            reverse("cinema:movie-list"), data={}
        )
        self.assertEqual(
            response_create.status_code, status.HTTP_401_UNAUTHORIZED
        )

        create_movie()
        response_retrieve = self.client.get(
            reverse("cinema:movie-detail", args=(1,))
        )
        self.assertEqual(
            response_retrieve.status_code, status.HTTP_401_UNAUTHORIZED
        )
