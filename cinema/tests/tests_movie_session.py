from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import Movie

MOVIE_SESSION_URL = reverse("cinema:moviesession-list")


# def sample_movie_session(**params):
#     movie = Movie.objects.create(
#         "test", 'test', "100",
#     )
#     cinema_hall
#
#
#     defaults = {
#
#     }
#     Movie_Seesion.ob



class UnauthenticatedMovieSessionApiTest(TestCase):
    def setup(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(MOVIE_SESSION_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class IsAuthenticated(TestCase):
    def setup(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create(
            "test@test.com", "user1234"
        )
        self.client.force_authenticate(self.user)
