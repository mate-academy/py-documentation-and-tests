from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


CREATE_USER_URL = reverse("user:create")
TOKEN_URL = reverse("user:token-obtain-pair")
TOKEN_REFRESH_URL = reverse("user:token-refresh")


def create_user(**params):
    return get_user_model().objects.create_user(**params)


class PublicUserApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_create_user_success(self):
        payload = {
            "email": "user@test.com",
            "password": "testpass123",
        }

        res = self.client.post(CREATE_USER_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertNotIn("password", res.data)
        self.assertTrue(
            get_user_model().objects.filter(email=payload["email"]).exists()
        )

    def test_create_jwt_token_for_user(self):
        payload = {
            "email": "user@test.com",
            "password": "testpass123",
        }
        create_user(**payload)

        res = self.client.post(TOKEN_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("access", res.data)
        self.assertIn("refresh", res.data)

    def test_refresh_jwt_token(self):
        payload = {
            "email": "user@test.com",
            "password": "testpass123",
        }
        create_user(**payload)
        token_res = self.client.post(TOKEN_URL, payload)

        res = self.client.post(
            TOKEN_REFRESH_URL,
            {"refresh": token_res.data["refresh"]},
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("access", res.data)
