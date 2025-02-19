from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from cinema.models import Movie, Genre, Actor

User = get_user_model()


class MovieViewSetTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin@example.com",
            password="adminpass",
            is_staff=True
        )
        self.user = User.objects.create_user(
            email="user@example.com",
            password="userpass"
        )

        # Create test data
        self.genre1 = Genre.objects.create(name="Action")
        self.genre2 = Genre.objects.create(name="Comedy")

        self.actor1 = Actor.objects.create(first_name="John", last_name="Doe")
        self.actor2 = Actor.objects.create(first_name="Jane", last_name="Smith")

        self.movie1 = Movie.objects.create(
            title="The Matrix",
            description="Sci-fi movie",
            duration=150
        )
        self.movie1.genres.add(self.genre1)
        self.movie1.actors.add(self.actor1)

        self.movie2 = Movie.objects.create(
            title="The Avengers",
            description="Superhero movie",
            duration=180
        )
        self.movie2.genres.add(self.genre1, self.genre2)
        self.movie2.actors.add(self.actor1, self.actor2)

        self.movie3 = Movie.objects.create(
            title="Inception",
            description="Dream movie",
            duration=160
        )
        self.movie3.genres.add(self.genre2)
        self.movie3.actors.add(self.actor2)

        self.list_url = reverse("movie-list")
        self.detail_url = reverse("movie-detail", args=[self.movie1.id])
        self.upload_image_url = reverse("movie-upload-image", args=[self.movie1.id])

    def test_movie_list_permissions(self):
        # Unauthenticated user
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Regular user
        self.client.force_authenticate(self.user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Admin user
        self.client.force_authenticate(self.admin)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_movie_create_permissions(self):
        data = {
            "title": "New Movie",
            "description": "Test description",
            "duration": 120,
            "genres": [self.genre1.id],
            "actors": [self.actor1.id]
        }

        # Unauthenticated user
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Regular user
        self.client.force_authenticate(self.user)
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Admin user
        self.client.force_authenticate(self.admin)
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_filter_movies_by_title(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(self.list_url, {"title": "matrix"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "The Matrix")

    def test_filter_movies_by_genres(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(
            self.list_url,
            {"genres": f"{self.genre2.id}"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # Avengers and Inception
        titles = {movie["title"] for movie in response.data}
        self.assertIn("The Avengers", titles)
        self.assertIn("Inception", titles)

    def test_filter_movies_by_actors(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(
            self.list_url,
            {"actors": f"{self.actor2.id}"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # Avengers and Inception
        titles = {movie["title"] for movie in response.data}
        self.assertIn("The Avengers", titles)
        self.assertIn("Inception", titles)

    def test_filter_movies_combined(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(
            self.list_url,
            {
                "title": "the",
                "genres": f"{self.genre1.id}",
                "actors": f"{self.actor1.id}"
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # Matrix and Avengers
        titles = {movie["title"] for movie in response.data}
        self.assertIn("The Matrix", titles)
        self.assertIn("The Avengers", titles)

    def test_retrieve_movie_detail(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "The Matrix")
        self.assertEqual(len(response.data["genres"]), 1)
        self.assertEqual(len(response.data["actors"]), 1)

    def test_serializer_classes(self):
        self.client.force_authenticate(self.user)

        # Test list serializer
        list_response = self.client.get(self.list_url)
        self.assertIn("image", list_response.data[0])
        self.assertIsInstance(list_response.data, list)

        # Test detail serializer
        detail_response = self.client.get(self.detail_url)
        self.assertIn("genres", detail_response.data)
        self.assertIsInstance(detail_response.data["genres"][0], dict)

    def test_upload_image_permissions(self):
        # Unauthenticated user
        response = self.client.post(self.upload_image_url, {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Regular user
        self.client.force_authenticate(self.user)
        response = self.client.post(self.upload_image_url, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Admin user
        self.client.force_authenticate(self.admin)
        response = self.client.post(self.upload_image_url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upload_image_valid(self):
        self.client.force_authenticate(self.admin)
        with open("cinema/tests/test_image.jpg", "rb") as image:
            response = self.client.post(
                self.upload_image_url,
                {"image": image},
                format="multipart"
            )
        self.movie1.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(self.movie1.image)
        self.assertIn("uploads/movies/", self.movie1.image.url)