from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from cinema.models import Actor
from cinema.serializers import ActorSerializer
from cinema.tests.test_base import sample_user, sample_actor, sample_admin_user

ACTOR_URL = reverse("cinema:actor-list")


class UnauthenticatedActorTests(TestCase):
    def test_auth_required(self):
        self.client = APIClient()
        res = self.client.get(ACTOR_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedActorTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = sample_user()
        self.client.force_authenticate(user=self.user)

    def test_actor_list(self):
        sample_actor()

        res = self.client.get(ACTOR_URL)

        actors = Actor.objects.all()
        serializer = ActorSerializer(actors, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_actor_forbidden(self):
        res = self.client.post(
            ACTOR_URL, {"first_name": "George", "last_name": "Clooney"}
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminActorTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = sample_admin_user()
        self.client.force_authenticate(user=self.user)

    def test_create_actor(self):
        payload = {"first_name": "George", "last_name": "Clooney"}

        res = self.client.post(ACTOR_URL, payload)
        actor = Actor.objects.get(id=res.data["id"])
        serializer = ActorSerializer(actor)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data, serializer.data)
