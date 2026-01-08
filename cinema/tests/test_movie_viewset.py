import tempfile
from PIL import Image
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from cinema.models import Movie, Genre, Actor

MOVIES_URL = reverse("cinema:movie-list")


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


def upload_image_url(movie_id):
    return reverse("cinema:movie-upload-image", args=[movie_id])


def create_user(**params):
    return get_user_model().objects.create_user(**params)


def create_admin(**params):
    return get_user_model().objects.create_superuser(**params)


class PublicMovieApiTests(APITestCase):
    def test_list_and_retrieve_movies_unauthenticated(self):
        movie = Movie.objects.create(title="Movie 1", description="Desc", duration=90)
        Movie.objects.create(title="Movie 2", description="Desc 2", duration=100)

        res = self.client.get(MOVIES_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

        res = self.client.get(detail_url(movie.id))
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_or_upload_not_allowed(self):
        movie = Movie.objects.create(title="Movie", description="Desc", duration=100)
        payload = {"title": "Movie", "description": "Desc", "duration": 100}

        res = self.client.post(MOVIES_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

        url = upload_image_url(movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            res = self.client.post(url, {"image": ntf}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateMovieApiTests(APITestCase):
    def setUp(self):
        self.user = create_user(email="user@test.com", password="testpass")
        self.client.force_authenticate(user=self.user)

    def test_list_movies_authenticated(self):
        Movie.objects.create(title="Movie 1", description="Desc", duration=90)
        res = self.client.get(MOVIES_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_user_cannot_create_or_upload(self):
        movie = Movie.objects.create(title="Movie", description="Desc", duration=100)
        payload = {"title": "Movie", "description": "Desc", "duration": 120}

        res = self.client.post(MOVIES_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        url = upload_image_url(movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            res = self.client.post(url, {"image": ntf}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_filter_movies(self):
        g1 = Genre.objects.create(name="Action")
        a1 = Actor.objects.create(first_name="Tom", last_name="Hanks")
        m1 = Movie.objects.create(title="M1", description="D1", duration=90)
        m1.genres.add(g1)
        m1.actors.add(a1)
        m2 = Movie.objects.create(title="M2", description="D2", duration=120)

        res = self.client.get(MOVIES_URL, {"title": "M1"})
        self.assertEqual(len(res.data), 1)

        res = self.client.get(MOVIES_URL, {"genres": f"{g1.id}"})
        self.assertEqual(len(res.data), 1)

        res = self.client.get(MOVIES_URL, {"actors": f"{a1.id}"})
        self.assertEqual(len(res.data), 1)


class AdminMovieApiTests(APITestCase):
    def setUp(self):
        self.admin_user = create_admin(email="admin@cinema.com", password="adminpass")
        self.client.force_authenticate(user=self.admin_user)

    def test_admin_create_and_upload(self):
        genre = Genre.objects.create(name="Action")
        actor = Actor.objects.create(first_name="Tom", last_name="Hanks")
        payload = {
            "title": "New Movie",
            "description": "Some description",
            "duration": 120,
            "genres": [genre.id],
            "actors": [actor.id],
        }

        res = self.client.post(MOVIES_URL, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        movie = Movie.objects.first()
        url = upload_image_url(movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(url, {"image": ntf}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        movie.refresh_from_db()
        self.assertTrue(movie.image)
