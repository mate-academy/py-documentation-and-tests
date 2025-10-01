# user/tests/test_auth_jwt.py

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase


class JwtAuthTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.token_url = reverse("cinema:token_obtain_pair")
        self.refresh_url = reverse("cinema:token_refresh")

        user_model = get_user_model()
        self.username_field = user_model.USERNAME_FIELD
        # Cria usuário usando o USERNAME_FIELD dinamicamente (email ou username)
        self.user = user_model.objects.create_user(
            **{self.username_field: "user@example.com"},
            password="test-pass-123",
        )

    def test_obtain_token_success(self):
        payload = {
            self.username_field: getattr(self.user, self.username_field),
            "password": "test-pass-123",
        }
        res = self.client.post(self.token_url, data=payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("access", res.data)
        self.assertIn("refresh", res.data)

    def test_obtain_token_bad_credentials(self):
        payload = {
            self.username_field: getattr(self.user, self.username_field),
            "password": "wrong-pass",
        }
        res = self.client.post(self.token_url, data=payload)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_token_success(self):
        # Primeiro, obtém o refresh
        login_payload = {
            self.username_field: getattr(self.user, self.username_field),
            "password": "test-pass-123",
        }
        res_login = self.client.post(self.token_url, data=login_payload)
        self.assertEqual(res_login.status_code, status.HTTP_200_OK)
        refresh = res_login.data.get("refresh")
        self.assertTrue(refresh)

        # Usa o refresh para obter novo access
        res_refresh = self.client.post(self.refresh_url, data={"refresh": refresh})
        self.assertEqual(res_refresh.status_code, status.HTTP_200_OK)
        self.assertIn("access", res_refresh.data)
