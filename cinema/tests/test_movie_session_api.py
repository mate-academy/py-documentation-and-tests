from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework.reverse import reverse
from rest_framework import status

from cinema.models import CinemaHall, MovieSession, Movie

MOVIE_SESSION_URL = reverse("cinema:moviesession-list")

class UnauthenticatedMovieSessionApiTestCase(APITestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(MOVIE_SESSION_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

class AuthenticatedMovieSessionApiTestCase(APITestCase):

    def setUp(self):
        self.client = APIClient()
        user = get_user_model().objects.create_user(email="test@testowski.com", password="password")
        self.client.force_authenticate(user)

    def sample_movie(self, **params):
        defaults = {
            "title": "Sample movie",
            "description": "Sample description",
            "duration": 90,
        }
        defaults.update(params)

        return Movie.objects.create(**defaults)

    def sample_movie_2(self, **params):
        defaults = {
            "title": "Sample movie2",
            "description": "Sample description2",
            "duration": 92,
        }
        defaults.update(params)

        return Movie.objects.create(**defaults)

    def sample_movie_session(self, **params):
        cinema_hall = CinemaHall.objects.create(
            name="Blue", rows=20, seats_in_row=20
        )

        defaults = {
            "show_time": "2021-10-08T13:00:00Z",
            "movie": self.sample_movie(),
            "cinema_hall": cinema_hall,
        }
        defaults.update(params)

        return MovieSession.objects.create(**defaults)

    def sample_movie_session_2(self, **params):
        cinema_hall = CinemaHall.objects.create(
            name="Red", rows=20, seats_in_row=20
        )

        defaults = {
            "show_time": "2022-10-08T13:00:00Z",
            "movie": self.sample_movie_2(),
            "cinema_hall": cinema_hall,
        }
        defaults.update(params)

        return MovieSession.objects.create(**defaults)

    def test_movie_session_list(self):
        movie_session = self.sample_movie_session()
        movie_session2 = self.sample_movie_session_2()
        response = self.client.get(MOVIE_SESSION_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 2)
        print(response.json())

    def test_movie_session_filtering_by_movie(self):

        movie_session_1 = self.sample_movie_session()
        movie_session_2 = self.sample_movie_session_2()

        filtering_params_movie_id = {"movie": 1}

        response = self.client.get(MOVIE_SESSION_URL, filtering_params_movie_id)
        session = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(session), 1)
        self.assertEqual(session[0]["id"], movie_session_1.id)

    def test_movie_session_filtering_by_date(self):

        movie_session_1 = self.sample_movie_session()
        movie_session_2 = self.sample_movie_session_2()

        filtering_params_session_date = {"date": "2022-10-08"}

        response = self.client.get(MOVIE_SESSION_URL, filtering_params_session_date)
        session = response.json()

        self.assertEqual(session[0]["show_time"], movie_session_2.show_time)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(session), 1)


    def test_single_session(self):
        movie_session = self.sample_movie_session()
        url = reverse("cinema:moviesession-detail", kwargs={"pk":movie_session.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        print(response.json())
        self.assertEqual(response.json()["cinema_hall"]["name"], "Blue")


    def test_create_session_not_allowed(self):
        payload = {
          "show_time": "2026-06-18T10:31:19.815Z",
          "movie": 1,
          "cinema_hall": 1
                  }
        response = self.client.post(MOVIE_SESSION_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(MovieSession.objects.filter(id=payload["movie"]), 1)


    def test_update_movie_session_put(self):
        movie_session = self.sample_movie_session()

        url = reverse("cinema:moviesession-detail", kwargs={"pk": movie_session.id})

        payload = {
            "show_time": "2025-01-01T12:00:00Z",
            "movie": movie_session.movie.id,
            "cinema_hall": movie_session.cinema_hall.id,
        }

        response = self.client.put(url, payload)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_movie_session_patch(self):
        movie_session = self.sample_movie_session()

        url = reverse("cinema:moviesession-detail", kwargs={"pk": movie_session.id})

        payload = {
            "show_time": "2025-02-02T15:00:00Z"
        }

        response = self.client.patch(url, payload)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_movie_session(self):
        movie_session = self.sample_movie_session()

        url = reverse("cinema:moviesession-detail", kwargs={"pk": movie_session.id})

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(MovieSession.objects.filter(id=movie_session.id).exists())