from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from cinema.models import Movie, CinemaHall, MovieSession
from django.utils import timezone


class MovieSessionTests(APITestCase):
    def setUp(self):
        self.hall = CinemaHall.objects.create(
            name='Hall 1',
            rows=10,
            seats_in_row=15
        )
        self.movie = Movie.objects.create(
            title='Test Movie',
            duration=120
        )
        self.session = MovieSession.objects.create(
            movie=self.movie,
            cinema_hall=self.hall,
            show_time=timezone.now()
        )

    def test_get_sessions(self):
        url = reverse('cinema:moviesession-list')  # Changed from 'movie-sessions-list'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_filter_sessions(self):
        url = reverse('cinema:moviesession-list')  # Changed from 'movie-sessions-list'
        date = timezone.now().date()
        response = self.client.get(f'{url}?date={date}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
