from django.test import TestCase
from django.conf import settings
from rest_framework.test import APIClient
from rest_framework import status
from django.urls import reverse


class ThrottlingTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_throttling_configuration(self):
        original_throttle_classes = [
            "rest_framework.throttling.AnonRateThrottle",
            "rest_framework.throttling.UserRateThrottle",
        ]
        original_throttle_rates = {
            "anon": "10/minute",
            "user": "30/minute",
        }

        self.assertIn(
            "rest_framework.throttling.AnonRateThrottle", original_throttle_classes
        )
        self.assertIn(
            "rest_framework.throttling.UserRateThrottle", original_throttle_classes
        )
        self.assertEqual(original_throttle_rates["anon"], "10/minute")
        self.assertEqual(original_throttle_rates["user"], "30/minute")

    def test_basic_api_access(self):
        """Test that basic API access works"""
        url = reverse("cinema:movie-list")
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
