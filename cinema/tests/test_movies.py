from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from cinema.models import Movie, Genre, Actor
from django.contrib.auth import get_user_model

User = get_user_model()


class MovieTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            email='admin@cinema.com',
            password='adminpass'
        )
        self.regular_user = User.objects.create_user(
            email='user@cinema.com',
            password='userpass'
        )
        self.genre = Genre.objects.create(name='Action')
        self.actor = Actor.objects.create(first_name='Tom', last_name='Cruise')
        self.movie = Movie.objects.create(
            title='Test Movie',
            description='Test Description',
            duration=120
        )
        self.movie.genres.add(self.genre)
        self.movie.actors.add(self.actor)

    def test_get_movies(self):
        url = reverse('cinema:movie-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_filter_movies(self):
        url = reverse('cinema:movie-list')

        # Test title filter
        response = self.client.get(f'{url}?title=Test')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

        # Test genre filter
        response = self.client.get(f'{url}?genres={self.genre.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

        # Test actor filter
        response = self.client.get(f'{url}?actors={self.actor.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_create_movie_unauthorized(self):
        url = reverse('cinema:movie-list')
        data = {
            'title': 'New Movie',
            'description': 'New Description',
            'duration': 150,
            'genres': [self.genre.id],
            'actors': [self.actor.id]
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_movie_authorized(self):
        self.client.force_authenticate(user=self.admin)
        url = reverse('cinema:movie-list')
        data = {
            'title': 'New Movie',
            'description': 'New Description',
            'duration': 150,
            'genres': [self.genre.id],
            'actors': [self.actor.id]
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Movie.objects.count(), 2)

    def test_create_movie_regular_user(self):
        self.client.force_authenticate(user=self.regular_user)
        url = reverse('cinema:movie-list')
        data = {
            'title': 'New Movie',
            'description': 'New Description',
            'duration': 150,
            'genres': [self.genre.id],
            'actors': [self.actor.id]
        }
        response = self.client.post(url, data, format='json')
        # Should fail unless regular users have permission
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
