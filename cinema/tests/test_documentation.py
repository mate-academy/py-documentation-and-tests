from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


class DocumentationTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_schema_is_available(self):
        response = self.client.get(
            reverse("api-schema"),
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        movie_parameters = response.data["paths"][
            "/api/cinema/movies/"
        ]["get"]["parameters"]
        session_parameters = response.data["paths"][
            "/api/cinema/movie_sessions/"
        ]["get"]["parameters"]

        self.assertEqual(
            {parameter["name"] for parameter in movie_parameters},
            {"actors", "genres", "title"},
        )
        self.assertEqual(
            {parameter["name"] for parameter in session_parameters},
            {"date", "movie"},
        )
        self.assertTrue(
            all(parameter.get("description") for parameter in movie_parameters)
        )
        self.assertTrue(
            all(
                parameter.get("description")
                for parameter in session_parameters
            )
        )

    def test_throttling_settings(self):
        rest_framework_settings = settings.REST_FRAMEWORK

        self.assertEqual(
            rest_framework_settings["DEFAULT_THROTTLE_RATES"],
            {"anon": "10/min", "user": "30/min"},
        )

