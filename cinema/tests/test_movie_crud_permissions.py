# cinema/tests/test_movie_crud_permissions.py

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from cinema.models import Actor, Genre, Movie


class MovieCrudPermissionsTests(APITestCase):
    """
    Cobre create/retrieve/update/partial_update/destroy do MovieViewSet,
    validando permissões para anônimo, autenticado não-staff e staff.
    """

    @staticmethod
    def _results(data):
        """
        Adapta o retorno para endpoints paginados do DRF.
        """
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "results" in data:
            return data["results"]
        return []

    def setUp(self):
        # Zera contadores de throttling entre testes
        cache.clear()

        self.client = APIClient()
        self.movie_list_url = reverse("cinema:movie-list")

        # Dados base
        self.genre = Genre.objects.create(name="Action")
        self.actor = Actor.objects.create(first_name="John", last_name="Doe")
        self.movie = Movie.objects.create(
            title="Seed",
            description="Seed desc",
            duration=90,
        )
        self.movie.genres.add(self.genre)
        self.movie.actors.add(self.actor)
        self.movie_detail_url = reverse("cinema:movie-detail", args=[self.movie.id])

        # Usuários
        user_model = get_user_model()
        self.username_field = user_model.USERNAME_FIELD

        self.user = user_model.objects.create_user(
            **{self.username_field: "user@example.com"},
            password="pass-123",
        )
        self.staff = user_model.objects.create_user(
            **{self.username_field: "admin@example.com"},
            password="pass-123",
            is_staff=True,
        )

    def test_anonymous_cannot_list_or_retrieve(self):
        # List
        res = self.client.get(self.movie_list_url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

        # Retrieve
        res = self.client.get(self.movie_detail_url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_user_can_list_and_retrieve_but_cannot_write(self):
        # Autentica como usuário não-staff
        self.client.force_authenticate(user=self.user)

        # List
        res = self.client.get(self.movie_list_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        items = self._results(res.data)
        self.assertTrue(any(i["title"] == "Seed" for i in items))

        # Retrieve
        res = self.client.get(self.movie_detail_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["title"], "Seed")

        # Create
        payload = {
            "title": "Blocked Create",
            "description": "X",
            "duration": 100,
            "genres": [self.genre.id],
            "actors": [self.actor.id],
        }
        res = self.client.post(self.movie_list_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        # Update (PUT)
        payload = {
            "title": "Blocked Put",
            "description": "Y",
            "duration": 101,
            "genres": [self.genre.id],
            "actors": [self.actor.id],
        }
        res = self.client.put(self.movie_detail_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        # Partial Update (PATCH)
        res = self.client.patch(
            self.movie_detail_url, {"title": "Nope"}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        # Destroy
        res = self.client.delete(self.movie_detail_url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_can_create_update_partial_update_and_destroy(self):
        # Autentica como staff
        self.client.force_authenticate(user=self.staff)

        # Create
        payload_create = {
            "title": "New Movie",
            "description": "Created",
            "duration": 120,
            "genres": [self.genre.id],
            "actors": [self.actor.id],
        }
        res = self.client.post(self.movie_list_url, payload_create, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        created_id = res.data["id"]
        created_detail = reverse("cinema:movie-detail", args=[created_id])

        # Retrieve do criado
        res = self.client.get(created_detail)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["title"], "New Movie")

        # Update (PUT)
        payload_put = {
            "title": "Updated Title",
            "description": "Updated Desc",
            "duration": 130,
            "genres": [self.genre.id],
            "actors": [self.actor.id],
        }
        res = self.client.put(created_detail, payload_put, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["title"], "Updated Title")
        self.assertEqual(res.data["duration"], 130)

        # Partial Update (PATCH)
        res = self.client.patch(
            created_detail, {"title": "Patched"}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["title"], "Patched")

        # Destroy
        res = self.client.delete(created_detail)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

        # Confirma que foi removido
        res = self.client.get(created_detail)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
