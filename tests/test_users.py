from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from user.models import User


class UserTests(APITestCase):
    def setUp(self):
        self.register_url = reverse("user:create")
        self.login_url = reverse("user:login")
        self.me_url = reverse("user:manage")

        self.user = User.objects.create_user(
            email="test@test.com", password="pass1234"
        )

    def test_register_user(self):
        payload = {"email": "new@test.com", "password": "newpass123"}
        response = self.client.post(self.register_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email="new@test.com").exists())

    def test_login_user(self):
        payload = {"email": "test@test.com", "password": "pass1234"}
        response = self.client.post(self.login_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)  # тепер перевіряємо access

    def test_login_invalid_credentials(self):
        payload = {"email": "test@test.com", "password": "wrongpass"}
        response = self.client.post(self.login_url, payload, format="json")
        self.assertEqual(
            response.status_code, status.HTTP_401_UNAUTHORIZED
        )  # JWT повертає 401

    def test_get_user_profile_authorized(self):
        payload = {"email": "test@test.com", "password": "pass1234"}
        login_response = self.client.post(
            self.login_url, payload, format="json"
        )
        access_token = login_response.data["access"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "test@test.com")

    def test_get_user_profile_unauthorized(self):
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
