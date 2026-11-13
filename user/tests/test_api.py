from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from user.models import User


REGISTER_URL = reverse("user:create")
TOKEN_URL = reverse("user:token_obtain_pair")
TOKEN_REFRESH_URL = reverse("user:token_refresh")
TOKEN_VERIFY_URL = reverse("user:token_verify")
ME_URL = reverse("user:manage")


class UserRegistrationTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_register_user(self):
        payload = {
            "email": "test@myproject.com",
            "password": "testpass123",
        }
        res = self.client.post(REGISTER_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 1)
        user = User.objects.get(email="test@myproject.com")
        self.assertTrue(user.check_password("testpass123"))

    def test_register_user_short_password(self):
        payload = {
            "email": "test@myproject.com",
            "password": "1234",
        }
        res = self.client.post(REGISTER_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_duplicate_email(self):
        payload = {
            "email": "test@myproject.com",
            "password": "testpass123",
        }
        self.client.post(REGISTER_URL, payload)
        res = self.client.post(REGISTER_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


class UserTokenTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="test@myproject.com",
            password="testpass123",
        )

    def test_obtain_token(self):
        payload = {
            "email": "test@myproject.com",
            "password": "testpass123",
        }
        res = self.client.post(TOKEN_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("access", res.data)
        self.assertIn("refresh", res.data)

    def test_obtain_token_wrong_password(self):
        payload = {
            "email": "test@myproject.com",
            "password": "wrongpassword",
        }
        res = self.client.post(TOKEN_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_obtain_token_nonexistent_user(self):
        payload = {
            "email": "nonexistent@myproject.com",
            "password": "testpass123",
        }
        res = self.client.post(TOKEN_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_obtain_token_missing_fields(self):
        payload = {
            "email": "test@myproject.com",
        }
        res = self.client.post(TOKEN_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


class ManageUserTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="test@myproject.com",
            password="testpass123",
        )
        self.client.force_authenticate(self.user)

    def test_get_current_user(self):
        res = self.client.get(ME_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["email"], "test@myproject.com")

    def test_update_user_password(self):
        res = self.client.patch(ME_URL, {
            "password": "newpassword123",
        })
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("newpassword123"))

    def test_unauthenticated_cannot_access_me(self):
        self.client.force_authenticate(None)
        res = self.client.get(ME_URL)
        self.assertIn(res.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
