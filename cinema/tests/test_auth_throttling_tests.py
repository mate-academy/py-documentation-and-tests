# cinema/tests/test_auth_throttling_tests.py

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from cinema.models import Genre, Actor, Movie, CinemaHall, MovieSession


class ThrottlingTests(APITestCase):
    def setUp(self):
        # Zera contadores de throttling entre testes
        cache.clear()

        self.client = APIClient()

        # URLs resolvidas em runtime (evita reverse() no import)
        self.schema_url = reverse("cinema:schema")
        self.movie_list_url = reverse("cinema:movie-list")
        self.token_url = reverse("cinema:token_obtain_pair")

        # Dados mínimos para respostas 200 estáveis
        self.genre = Genre.objects.create(name="Action")
        self.actor = Actor.objects.create(first_name="John", last_name="Doe")
        self.movie = Movie.objects.create(
            title="Sample",
            description="Desc",
            duration=120,
        )
        self.movie.genres.add(self.genre)
        self.movie.actors.add(self.actor)

        self.hall = CinemaHall.objects.create(
            name="Hall 1",
            rows=5,
            seats_in_row=10,
        )
        MovieSession.objects.create(
            movie=self.movie,
            cinema_hall=self.hall,
            show_time=timezone.now(),
        )

        # Usuário para testes autenticados
        user_model = get_user_model()
        self.username_field = user_model.USERNAME_FIELD
        self.user = user_model.objects.create_user(
            **{self.username_field: "user@example.com"},
            password="test-pass-123",
        )

    def _auth(self) -> None:
        # Zera contadores antes de autenticar para evitar 429
        cache.clear()

        payload = {
            self.username_field: getattr(self.user, self.username_field),
            "password": "test-pass-123",
        }
        res = self.client.post(self.token_url, data=payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        access = res.data.get("access")
        self.assertTrue(access)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    def test_anon_throttle_schema_endpoint(self):
        """
        Deve permitir até 10 requisições anônimas por minuto e
        retornar 429 na 11ª, conforme settings.DEFAULT_THROTTLE_RATES.
        """
        for _ in range(10):
            res = self.client.get(self.schema_url)
            self.assertEqual(res.status_code, status.HTTP_200_OK)

        res = self.client.get(self.schema_url)
        self.assertEqual(res.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_user_throttle_movie_list(self):
        """
        Deve permitir até 30 requisições autenticadas por minuto e
        retornar 429 na 31ª.
        """
        self._auth()

        for _ in range(30):
            res = self.client.get(self.movie_list_url)
            self.assertEqual(res.status_code, status.HTTP_200_OK)

        res = self.client.get(self.movie_list_url)
        self.assertEqual(res.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
