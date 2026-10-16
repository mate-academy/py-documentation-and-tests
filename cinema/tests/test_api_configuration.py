from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken


class APIConfigurationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            "viewer@example.com", "strong-password"
        )

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.client = APIClient()

    def authenticate(self):
        token = AccessToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_jwt_login_authenticates_all_protected_resources(self):
        response = self.client.post(
            "/api/user/token/",
            {"email": self.user.email, "password": "strong-password"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("refresh", response.data)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {response.data['access']}"
        )
        for path in (
            "cinema/genres/",
            "cinema/actors/",
            "cinema/cinema_halls/",
            "cinema/movies/",
            "cinema/movie_sessions/",
            "cinema/orders/",
            "user/me/",
        ):
            with self.subTest(path=path):
                result = self.client.get(f"/api/{path}")
                self.assertEqual(result.status_code, status.HTTP_200_OK)

    def test_jwt_refresh_and_verify(self):
        response = self.client.post(
            "/api/user/token/",
            {"email": self.user.email, "password": "strong-password"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        refreshed = self.client.post(
            "/api/user/token/refresh/", {"refresh": response.data["refresh"]}
        )
        self.assertEqual(refreshed.status_code, status.HTTP_200_OK)
        verified = self.client.post(
            "/api/user/token/verify/", {"token": refreshed.data["access"]}
        )
        self.assertEqual(verified.status_code, status.HTTP_200_OK)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {refreshed.data['access']}"
        )
        profile = self.client.get("/api/user/me/")
        self.assertEqual(profile.data["email"], self.user.email)

    def test_jwt_rejects_invalid_credentials(self):
        response = self.client.post(
            "/api/user/token/",
            {"email": self.user.email, "password": "wrong-password"},
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn("access", response.data)

    def test_jwt_rejects_invalid_refresh_token(self):
        response = self.client.post(
            "/api/user/token/refresh/", {"refresh": "invalid-token"}
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_jwt_rejects_expired_and_invalid_access_tokens(self):
        expired = AccessToken.for_user(self.user)
        expired.set_exp(lifetime=timedelta(seconds=-60))
        for token in (str(expired), "invalid-token"):
            with self.subTest(token=token):
                self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
                response = self.client.get("/api/cinema/movies/")
                self.assertEqual(
                    response.status_code, status.HTTP_401_UNAUTHORIZED
                )

    def test_existing_token_authentication_still_works(self):
        token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        response = self.client.get("/api/cinema/movies/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_anonymous_requests_are_limited_to_ten_per_minute(self):
        for _ in range(10):
            response = self.client.post("/api/user/register/", {})
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response = self.client.post("/api/user/register/", {})
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertGreater(int(response["Retry-After"]), 0)

    def test_legacy_login_is_throttled(self):
        for _ in range(10):
            response = self.client.post("/api/user/login/", {})
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response = self.client.post("/api/user/login/", {})
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_authenticated_requests_are_limited_to_thirty_per_minute(self):
        self.authenticate()
        for _ in range(30):
            response = self.client.get("/api/cinema/movies/")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.client.get("/api/cinema/movies/")
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertGreater(int(response["Retry-After"]), 0)

    def test_schema_documents_all_resources_filters_and_jwt(self):
        response = self.client.get(
            "/api/schema/", HTTP_ACCEPT="application/vnd.oai.openapi+json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        schema = response.data
        for resource in (
            "genres", "actors", "cinema_halls", "movies",
            "movie_sessions", "orders",
        ):
            self.assertIn(f"/api/cinema/{resource}/", schema["paths"])
        self.assertIn("/api/user/register/", schema["paths"])
        self.assertIn("/api/user/me/", schema["paths"])
        self.assertIn("/api/user/token/", schema["paths"])
        for path, expected in (
            ("/api/cinema/movies/", {"title", "genres", "actors"}),
            ("/api/cinema/movie_sessions/", {"date", "movie"}),
        ):
            parameters = schema["paths"][path]["get"]["parameters"]
            query = {p["name"]: p for p in parameters if p["in"] == "query"}
            self.assertEqual(set(query), expected)
            for parameter in query.values():
                self.assertTrue(parameter["description"])
        security = schema["components"]["securitySchemes"]
        self.assertEqual(security["jwtAuth"]["scheme"], "bearer")
        upload = schema["paths"][
            "/api/cinema/movies/{id}/upload-image/"
        ]["post"]
        self.assertIn("multipart/form-data", upload["requestBody"]["content"])

    def test_swagger_and_redoc_pages_are_available(self):
        for path in ("/api/doc/swagger/", "/api/doc/redoc/"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertContains(response, "/api/schema/")
