from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from cinema.models import Genre
from cinema.serializers import GenreSerializer
from cinema.tests.test_base import sample_user, sample_genre, sample_admin_user

GENRE_URL = reverse("cinema:genre-list")


class UnauthenticatedGenreTests(TestCase):
    def test_auth_required(self):
        self.client = APIClient()
        res = self.client.get(GENRE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedGenreTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = sample_user()
        self.client.force_authenticate(self.user)

    def test_genre_list(self):
        sample_genre()
        res = self.client.get(GENRE_URL)

        genres = Genre.objects.all()
        serializer = GenreSerializer(genres, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_genre_forbidden(self):
        res = self.client.post(GENRE_URL, {"name": "drama"})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminGenreTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = sample_admin_user()
        self.client.force_authenticate(self.user)

    def test_create_genre(self):
        payload = {"name": "drama"}

        res = self.client.post(GENRE_URL, payload)
        genre = Genre.objects.get(id=res.data["id"])
        serializer = GenreSerializer(genre)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data, serializer.data)
