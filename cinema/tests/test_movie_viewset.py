from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from cinema.models import Genre, Actor, CinemaHall, Movie, MovieSession, Order
from django.core.files.uploadedfile import SimpleUploadedFile
import tempfile
from PIL import Image


def image_file():
    img = Image.new("RGB", (100, 100), color="red")
    tmp_file = tempfile.NamedTemporaryFile(suffix=".jpg")
    img.save(tmp_file, format="JPEG")
    tmp_file.seek(0)
    return tmp_file


class AuthenticatedUserTestCase(APITestCase):
    def setUp(self):
        self.user_password = "testpass123"
        self.user = get_user_model().objects.create_user(
            email="user@test.com", password=self.user_password
        )
        self.client = APIClient()

        token_res = self.client.post(
            reverse("token_obtain_pair"),  # або "/api/token/"
            {"email": self.user.email, "password": self.user_password},
        )
        self.assertEqual(token_res.status_code, 200)
        access = token_res.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")


class GenreTests(AuthenticatedUserTestCase):
    def test_list_genres(self):
        Genre.objects.create(name="Action")
        res = self.client.get(reverse("cinema:genre-list"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)

    def test_create_genre_as_non_admin(self):
        res = self.client.post(reverse("cinema:genre-list"), {"name": "Drama"})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class ActorTests(AuthenticatedUserTestCase):
    def test_list_actors(self):
        Actor.objects.create(first_name="Tom", last_name="Hanks")
        res = self.client.get(reverse("cinema:actor-list"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)


class MovieTests(AuthenticatedUserTestCase):
    def setUp(self):
        super().setUp()
        self.movie = Movie.objects.create(
            title="Test movie", description="desc", duration=100
        )

    def test_list_movies(self):
        res = self.client.get(reverse("cinema:movie-list"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)

    def test_upload_image(self):
        admin = get_user_model().objects.create_superuser(
            email="admin@test.com", password="admin123"
        )
        self.client.force_authenticate(user=admin)
        url = reverse("cinema:movie-upload-image", args=[self.movie.id])
        with image_file() as img:
            res = self.client.post(url, {"image": img}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.movie.refresh_from_db()
        self.assertTrue(bool(self.movie.image))


class MovieSessionTests(AuthenticatedUserTestCase):
    def setUp(self):
        super().setUp()
        hall = CinemaHall.objects.create(name="Big", rows=5, seats_in_row=5)
        self.movie = Movie.objects.create(
            title="Session movie", description="desc", duration=120
        )
        self.session = MovieSession.objects.create(
            movie=self.movie, cinema_hall=hall, show_time="2025-09-01T12:00:00Z"
        )

    def test_list_sessions(self):
        res = self.client.get(reverse("cinema:moviesession-list"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)

    def test_filter_by_movie(self):
        url = reverse("cinema:moviesession-list")
        res = self.client.get(url, {"movie": self.movie.id})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data[0]["movie_title"], self.movie.title)


class OrderTests(AuthenticatedUserTestCase):
    def test_create_order(self):
        hall = CinemaHall.objects.create(name="Small", rows=2, seats_in_row=2)
        movie = Movie.objects.create(
            title="Order movie", description="desc", duration=90
        )
        session = MovieSession.objects.create(
            movie=movie, cinema_hall=hall, show_time="2025-09-01T18:00:00Z"
        )

        url = reverse("cinema:order-list")
        payload = {
            "tickets": [
                {"row": 1, "seat": 1, "movie_session": session.id},
                {"row": 1, "seat": 2, "movie_session": session.id},
            ]
        }
        res = self.client.post(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(Order.objects.first().tickets.count(), 2)

    def test_list_orders_user_only(self):
        Order.objects.create(user=self.user)
        other = get_user_model().objects.create_user(
            email="other@test.com", password="123456"
        )
        Order.objects.create(user=other)

        res = self.client.get(reverse("cinema:order-list"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 1)
