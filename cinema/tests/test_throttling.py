from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class ThrottlingTests(APITestCase):
    def test_anon_throttling(self):
        url = reverse('cinema:movie-list')
        for _ in range(11):  # 10 разрешено + 1 лишний
            response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_user_throttling(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.create_user(
            email='test@user.com',
            password='testpass'
        )
        self.client.force_authenticate(user=user)

        url = reverse('cinema:movie-list')
        for _ in range(31):  # 30 разрешено + 1 лишний
            response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
