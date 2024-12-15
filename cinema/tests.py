from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient
from unittest import TestCase

from cinema.models import Movie
from cinema.serializers import MovieSerializer


MOVIE_URL = reverse('cinema:movie-list')


def create_a_movie():
    return Movie.objects.create(name='Test Movie',
                         description='Test Movie Description',
                         duration=60,
                         )


class UnauthenticatedTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(email='<EMAIL>', password='<PASSWORD>')

    def test_unauthenticated(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

class AuthenticatedTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(email='<EMAIL>', password='<PASSWORD>')
        self.client.force_authenticate(user=self.user)

    def movie_list(self):
        movie = create_a_movie()
        serializer = MovieSerializer(movie)
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)
        
    def movie_create(self):
        movie = create_a_movie()
        res = self.client.post(MOVIE_URL, **movie)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def movie_retrieve(self):
        movie = create_a_movie()
        serializer = MovieSerializer(movie)
        res = self.client.get(MOVIE_URL, {'id': movie.id})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def movie_update(self):
        movie = create_a_movie()
        res = self.client.patch(MOVIE_URL, {'id': movie.id, 'name': 'Test Movie 2',})
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        
    def movie_delete(self):
        movie = create_a_movie()
        res = self.client.delete(MOVIE_URL, {'id': movie.id})
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AdminTests(AuthenticatedTests):
    def setUp(self):
        client = APIClient()
        user = super(AuthenticatedTests, self).setUp()
        client.force_authenticate(user=user)

    def movie_list(self):
        movie = create_a_movie()
        serializer = MovieSerializer(movie)
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def movie_create(self):
        movie = create_a_movie()
        res = self.client.post(MOVIE_URL, **movie)
        serializer = MovieSerializer(movie)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data, serializer.data)

    def movie_retrieve(self):
        movie = create_a_movie()
        serializer = MovieSerializer(movie)
        res = self.client.get(MOVIE_URL, {'id': movie.id})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def movie_update(self):
        movie = create_a_movie()
        res = self.client.patch(MOVIE_URL, {'id': movie.id, 'name': 'Test Movie 2', })
        serializer = MovieSerializer(movie)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)


    def movie_delete(self):
        movie = create_a_movie()
        res = self.client.delete(MOVIE_URL, {'id': movie.id})
        self.assertEqual(res.status_code, status.HTTP_200_OK)

