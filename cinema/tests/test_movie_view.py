from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from cinema.models import Movie, Genre, Actor

MOVIE_URL = reverse("cinema:movie-list")


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


def upload_image_url(movie_id):
    return reverse("cinema:movie-upload-image", args=[movie_id])


class UnauthenticatedMovieViewSetTests(APITestCase):
    def setUp(self):
        self.genre = Genre.objects.create(name="Action")
        self.actor = Actor.objects.create(first_name="John", last_name="Doe")
        self.movie = Movie.objects.create(
            title="Inception",
            description="A sci-fi thriller",
            duration=148
        )
        self.movie.genres.add(self.genre)
        self.movie.actors.add(self.actor)

    def test_auth_required_for_list(self):

        response = self.client.get(MOVIE_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_auth_required_for_detail(self):

        response = self.client.get(detail_url(self.movie.id))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_forbidden_to_create_movie(self):
        payload = {
            "title": "Interstellar",
            "description": "Space travel",
            "duration": 169
        }
        response = self.client.post(MOVIE_URL, payload)
        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
        )


class AuthenticatedMovieViewSetTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="user@test.com",
            password="password123"
        )
        self.client.force_authenticate(user=self.user)

    def test_regular_user_forbidden_to_create_movie(self):
        payload = {
            "title": "Interstellar",
            "description": "Space travel",
            "duration": 169
        }
        response = self.client.post(MOVIE_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieViewSetTests(APITestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            email="admin@test.com",
            password="adminpassword123"
        )
        self.client.force_authenticate(user=self.admin)

        self.genre = Genre.objects.create(name="Sci-Fi")
        self.actor = Actor.objects.create(first_name="Matthew", last_name="McConaughey")

    def test_admin_can_create_movie(self):
        payload = {
            "title": "Interstellar",
            "description": "Space travel and survival",
            "duration": 169,
            "genres": [self.genre.id],
            "actors": [self.actor.id],
        }
        response = self.client.post(MOVIE_URL, payload)

        if response.status_code != status.HTTP_201_CREATED:
            print("SERVER ERROR DATA:", response.data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        exists = Movie.objects.filter(title="Interstellar").exists()
        self.assertTrue(exists)


class MovieFilteringTests(APITestCase):
    def setUp(self):
        self.user1 = get_user_model().objects.create_user(
            email="user@test.com",
            password="password123"
        )
        self.client.force_authenticate(user=self.user1)

        self.genre1 = Genre.objects.create(name="Action")
        self.genre2 = Genre.objects.create(name="Comedy")

        self.actor1 = Actor.objects.create(first_name="Brad", last_name="Pitt")
        self.actor2 = Actor.objects.create(first_name="Tom", last_name="Cruise")

        self.movie1 = Movie.objects.create(title="Action Movie 1", duration=120)
        self.movie2 = Movie.objects.create(title="Comedy Movie 2", duration=90)

        self.movie1.genres.add(self.genre1)
        self.movie1.actors.add(self.actor1)

        self.movie2.genres.add(self.genre2)
        self.movie2.actors.add(self.actor2)

    def test_filter_by_title(self):
        response = self.client.get(MOVIE_URL, {"title": "action"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], self.movie1.title)

    def test_filter_by_genres(self):
        response = self.client.get(MOVIE_URL, {"genres": f"{self.genre2.id}"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], self.movie2.title)

    def test_filter_by_actors(self):
        response = self.client.get(MOVIE_URL, {"actors": f"{self.actor1.id}"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], self.movie1.title)
