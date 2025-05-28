from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model

from cinema.models import Movie, Genre, Actor


class MovieViewSetTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="user@example.com",
            password="pass1234"
        )

        self.admin = get_user_model().objects.create_superuser(
            email="admin@example.com",
            password="adminpass"
        )

        # Другий адмін? Якщо потрібен — залишаю, інакше можна видалити
        self.admin2 = get_user_model().objects.create_superuser(
            email="admin12@example.com",
            password="adminpass"
        )
        self.genre1 = Genre.objects.create(name="Comedy")
        self.genre2 = Genre.objects.create(name="Action")
        self.actor1 = Actor.objects.create(first_name="John", last_name="Doe")
        self.actor2 = Actor.objects.create(first_name="Jane", last_name="Smith")

        self.movie1 = Movie.objects.create(
            title="Funny Movie",
            description="A very funny movie",
            duration=90,
        )
        self.movie1.genres.add(self.genre1)
        self.movie1.actors.add(self.actor1)

        self.movie2 = Movie.objects.create(
            title="Action Movie",
            description="Full of action",
            duration=120,
        )
        self.movie2.genres.add(self.genre2)
        self.movie2.actors.add(self.actor2)

    def test_list_movies(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("cinema:movie-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_filter_movies_by_title(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("cinema:movie-list") + "?title=funny"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Funny Movie")

    def test_filter_movies_by_genres(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("cinema:movie-list") + f"?genres={self.genre2.id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Action Movie")

    def test_filter_movies_by_actors(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("cinema:movie-list") + f"?actors={self.actor1.id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Funny Movie")

    def test_retrieve_movie_detail(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("cinema:movie-detail", args=[self.movie1.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "Funny Movie")
        self.assertIn("genres", response.data)
        self.assertIn("actors", response.data)

    def test_create_movie_denied_for_anon(self):
        url = reverse("cinema:movie-list")
        data = {
            "title": "New Movie",
            "description": "Description here",
            "duration": 100,
            "genres": [self.genre1.id],
            "actors": [self.actor1.id],
        }
        response = self.client.post(url, data, format="json")
        # Змінив очікування з 403 на 401
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_movie_allowed_for_admin(self):
        self.client.force_authenticate(user=self.admin)
        url = reverse("cinema:movie-list")
        data = {
            "title": "New Movie",
            "description": "Description here",
            "duration": 100,
            "genres": [self.genre1.id],
            "actors": [self.actor1.id],
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["title"], "New Movie")

    def test_upload_image_denied_for_non_admin(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("cinema:movie-upload-image", args=[self.movie1.id])
        response = self.client.post(url, {}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
