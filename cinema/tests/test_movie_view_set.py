from io import BytesIO

from PIL import Image
from rest_framework.test import APITestCase

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.core.files.uploadedfile import SimpleUploadedFile

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer


class MovieViewSetTests(APITestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test_admin@test.com",
            password="test",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)

        self.save_genres_1 = Genre.objects.create(name="Fantasy")
        self.save_genres_2 = Genre.objects.create(name="Action")
        self.save_actors_1 = Actor.objects.create(first_name="Baki", last_name="Hanma")
        self.save_actors_2 = Actor.objects.create(first_name="Yujiro", last_name="Hanma")

    def test_item_list(self) -> None:
        url = reverse("cinema:movie-list")
        res = self.client.get(url)

        items = Movie.objects.all()
        serializer = MovieListSerializer(items, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(serializer.data, res.data)

    def test_item_detail(self) -> None:
        item = Movie.objects.create(
            title="test",
            description="test12211221",
            duration=120,
        )

        item.genres.set([self.save_genres_1])
        item.actors.set([self.save_actors_2])

        url = reverse("cinema:movie-detail", args=[item.id])
        res = self.client.get(url)

        serializer = MovieDetailSerializer(item)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(serializer.data, res.data)

    def test_item_create(self) -> None:
        payload = {
            "title": "Test_title",
            "description": "Test_description",
            "duration": 90,
            "genres": [self.save_genres_1.id],
            "actors": [self.save_actors_2.id],
        }

        url = reverse("cinema:movie-list")
        res = self.client.post(url, data=payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Movie.objects.count(), 1)

    def test_filter_movies_by_title(self) -> None:
        movie_1 = {"title": "Matrix", "description": "Matrix", "duration": 90}
        movie_2 = {"title": "Avatar", "description": "Avatar", "duration": 90}

        Movie.objects.create(**movie_1)
        Movie.objects.create(**movie_2)

        url = reverse("cinema:movie-list")
        res = self.client.get(url, data={"title": "Matrix"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], "Matrix")

    def test_filter_movies_by_genres(self) -> None:
        movie_genres_1 = Movie.objects.create(
            title="Matrix",
            description="Matrix",
            duration=90,
        )
        movie_genres_2 = Movie.objects.create(
            title="Avatar",
            description="Avatar",
            duration=90,
        )

        movie_genres_1.genres.set([self.save_genres_1])
        movie_genres_2.genres.set([self.save_genres_2])

        url = reverse("cinema:movie-list")
        res = self.client.get(url, {"genres": f"{self.save_genres_1.id}"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)

    def test_filter_movies_by_actors(self) -> None:
        movie_actors_1 = Movie.objects.create(
            title="Matrix",
            description="Matrix",
            duration=90,
        )
        movie_actors_2 = Movie.objects.create(
            title="Avatar",
            description="Avatar",
            duration=90,
        )

        movie_actors_1.actors.set([self.save_actors_1])
        movie_actors_2.actors.set([self.save_actors_2])

        url = reverse("cinema:movie-list")
        res = self.client.get(url, {"actors": f"{self.save_actors_1.id}"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)

    def test_movie_image_view(self) -> None:
        movie_image = Movie.objects.create(
            title="Matrix",
            description="Matrix",
            duration=90,
        )

        img = Image.new("RGB", (90, 90))
        buffered = BytesIO()
        img.save(buffered, format="JPEG")
        buffered.seek(0)

        file_data = SimpleUploadedFile(
            "test.jpg",
            buffered.read(),
            content_type="image/jpeg"
        )

        url = reverse("cinema:movie-upload-image", args=[movie_image.id])
        res = self.client.post(url, data={"image": file_data}, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_movie_image_upload_forbidden_for_non_admin(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test_user@test.com",
            password="test",
        )
        self.client.force_authenticate(self.user)

        movie_image = Movie.objects.create(
            title="Matrix",
            description="Matrix",
            duration=90,
        )

        img = Image.new("RGB", (90, 90))
        buffered = BytesIO()
        img.save(buffered, format="JPEG")
        buffered.seek(0)

        file_data = SimpleUploadedFile(
            "test.jpg",
            buffered.read(),
            content_type="image/jpeg"
        )

        url = reverse("cinema:movie-upload-image", args=[movie_image.id])
        res = self.client.post(url, data={"image": file_data}, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)