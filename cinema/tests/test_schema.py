from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient


class ApiDocumentationTests(TestCase):
    def setUp(self) -> None:
        cache.clear()
        self.client = APIClient()

    def test_schema_documents_filters_jwt_and_uploads(self) -> None:
        response = self.client.get(
            reverse("api-schema"), HTTP_ACCEPT="application/vnd.oai.openapi+json"
        )
        self.assertEqual(response.status_code, 200)
        schema = response.data
        for path, names in (
            ("/api/cinema/movies/", {"title", "genres", "actors"}),
            ("/api/cinema/movie_sessions/", {"date", "movie"}),
        ):
            parameters = schema["paths"][path]["get"]["parameters"]
            self.assertEqual({p["name"] for p in parameters}, names)
            self.assertTrue(all(p.get("description") for p in parameters))
        security = schema["components"]["securitySchemes"]["jwtAuth"]
        self.assertEqual(security["scheme"], "bearer")
        self.assertIn("/api/user/token/refresh/", schema["paths"])
        upload = schema["paths"][
            "/api/cinema/movies/{id}/upload-image/"
        ]["post"]
        self.assertIn("multipart/form-data", upload["requestBody"]["content"])

    def test_documentation_pages_are_accessible(self) -> None:
        for name in ("swagger-ui", "redoc"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200)
