from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model

User = get_user_model()


class UserAPITests(APITestCase):
    def setUp(self):
        self.user_data = {
            'email': 'test@user.com',
            'password': 'testpass123'
        }
        self.admin = User.objects.create_superuser(
            email='admin.user@cinema.com',
            password='1qazcde3'
        )
        self.regular_user = User.objects.create_user(
            email='regular@user.com',
            password='regularpass'
        )

    def test_user_registration(self):
        url = reverse('user:create')
        response = self.client.post(url, self.user_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email=self.user_data['email']).exists())

    def test_token_obtain(self):
        url = reverse('token_obtain_pair')  # Changed from 'user:login'
        response = self.client.post(url, {
            'email': 'admin.user@cinema.com',
            'password': '1qazcde3'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_unauthorized_access(self):
        url = reverse('cinema:movie-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_token_refresh(self):
        # First get access token
        response = self.client.post(
            reverse('token_obtain_pair'),
            {'email': 'admin.user@cinema.com', 'password': '1qazcde3'},
            format='json'
        )
        refresh_token = response.data['refresh']

        # Then refresh it
        response = self.client.post(
            reverse('token_refresh'),
            {'refresh': refresh_token},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
