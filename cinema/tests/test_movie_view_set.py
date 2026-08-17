import tempfile
from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieDetailSerializer

BASE_URL = reverse("cinema:movie-list")


class UnauthenticatedCinemaApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_unauthenticated_user_not_get_movie_list(self):
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedCinemaApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            email="test@test.test",
            password="testpassword"
        )
        self.genre1 = Genre.objects.create(name="Fiction")
        self.genre2 = Genre.objects.create(name="Action")
        self.genre3 = Genre.objects.create(name="Drama")

        self.actor1 = Actor.objects.create(first_name="Actor", last_name="1")
        self.actor2 = Actor.objects.create(first_name="Actor", last_name="2")
        self.actor3 = Actor.objects.create(first_name="Actor", last_name="3")

        self.movie_1 = Movie.objects.create(
            title="Test Movie",
            description="Test Movie Description",
            duration=60
        )
        self.movie_1.genres.set([self.genre1, self.genre2])
        self.movie_1.actors.set([self.actor1, self.actor2])

        self.movie_2 = Movie.objects.create(
            title="Another Movie",
            description="Another Movie Description",
            duration=50
        )
        self.movie_2.genres.set([self.genre3])
        self.movie_2.actors.set([self.actor3])

        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

    def test_authenticated_user_can_get_movie_list(self):
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_upload_image_to_movie(self):
        url = reverse("cinema:movie-upload-image", args=[self.movie_1.id])
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (30, 30))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            response = self.client.post(
                url,
                {"image": ntf},
                format="multipart"
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.movie_1.refresh_from_db()
        self.assertTrue(self.movie_1.image)

    def test_upload_invalid_image(self):
        url = reverse("cinema:movie-upload-image", args=[self.movie_1.id])
        response = self.client.post(
            url,
            {"image": "testtesttesttest"},
            format="multipart"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_image_upload_forbidden_for_regular_user(self):
        user = get_user_model().objects.create_user(
            email="test@www.com",
            password="1234qweasdzx"
        )
        refresh = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        url = reverse("cinema:movie-upload-image", args=[self.movie_1.id])
        response = self.client.post(
            url,
            {"image": "test_nothing"},
            format="multipart"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_filter_movies_by_title(self):
        response = self.client.get(BASE_URL, {"title": "test"})
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Test Movie")

    def test_filter_movies_by_genres(self):
        response = self.client.get(
            BASE_URL,
            {"genres": f"{self.genre1.id},{self.genre2.id}"}
        )
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Test Movie")

    def test_filter_movies_by_actors(self):
        response = self.client.get(
            BASE_URL,
            {"actors": f"{self.actor1.id},{self.actor2.id}"}
        )
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Test Movie")

    def test_retrieve_movie_detail(self):
        response = self.client.get(
            reverse(
                "cinema:movie-detail",
                args=[self.movie_1.id]
            )
        )
        serializer = MovieDetailSerializer(self.movie_1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_create_movie(self):
        new_movie = {
            "title": "New Movie",
            "description": "New Movie Description",
            "duration": 60,
            "genres": [self.genre1.id],
            "actors": [self.actor1.id]
        }
        response = self.client.post(BASE_URL, new_movie)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["title"], new_movie["title"])
