from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from cinema.models import CinemaHall, Movie, MovieSession, Order, Ticket
from django.contrib.auth import get_user_model

User = get_user_model()

class OrderTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='user@test.com',
            password='testpass123'
        )
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
            show_time='2023-01-01T12:00:00Z'
        )
        self.client.force_authenticate(user=self.user)

    def test_create_order(self):
        url = reverse('cinema:order-list')
        data = {
            'tickets': [
                {
                    'movie_session': self.session.id,
                    'row': 1,
                    'seat': 1
                }
            ]
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(Ticket.objects.count(), 1)

    def test_order_history(self):
        order = Order.objects.create(user=self.user)
        Ticket.objects.create(
            movie_session=self.session,
            order=order,
            row=1,
            seat=1
        )
        url = reverse('cinema:order-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
