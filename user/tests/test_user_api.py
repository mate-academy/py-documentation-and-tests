from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

User = get_user_model()


class PublicMeApiTests(APITestCase):
    def setUp(self):
        self.client = APIClient()

    def test_me_requires_auth(self):
        url = reverse("user:me")
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateMeApiTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.email = "user@example.com"
        self.password = "testpass123"
        self.user = User.objects.create_user(email=self.email, password=self.password)

        # отримуємо реальний JWT і ставимо Bearer
        token_url = reverse("user:login")  # або 'token_obtain_pair', якщо так назвав у root urls
        res = self.client.post(token_url, {"email": self.email, "password": self.password})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")

    def test_get_me_success(self):
        url = reverse("user:me")
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], self.user.id)
        self.assertEqual(res.data["email"], self.email)
        self.assertIn("is_staff", res.data)

    def test_update_me_email_and_password(self):
        url = reverse("user:me")
        payload = {"email": "new@example.com", "password": "newpass123"}
        res = self.client.patch(url, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "new@example.com")
        self.assertTrue(self.user.check_password("newpass123"))

    def test_post_not_allowed_on_me(self):
        url = reverse("user:me")
        res = self.client.post(url, {})
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)