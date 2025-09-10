from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from PIL import Image
import io
from django.core.files.uploadedfile import SimpleUploadedFile

MOVIES_URL = reverse("cinema:movie-list")

def detail_url(movie_id: int) -> str:
    from django.urls import reverse
    return reverse("cinema:movie-detail", args=[movie_id])

def image_upload_url(movie_id: int) -> str:
    from django.urls import reverse
    return reverse("cinema:movie-upload-image", args=[movie_id])

def jwt_auth(client: APIClient, email: str, password: str) -> None:
    res = client.post(reverse("user:login"), {"email": email, "password": password}, format="json")
    token = res.data["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

def sample_genre(name="Drama"):
    from cinema.models import Genre
    return Genre.objects.create(name=name)

def sample_actor(first_name="Emma", last_name="Watson"):
    from cinema.models import Actor
    return Actor.objects.create(first_name=first_name, last_name=last_name)

def sample_movie(title="Sample"):
    from cinema.models import Movie
    m = Movie.objects.create(title=title, description="Desc", duration=90)
    return m


class PublicMovieViewSetTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required_for_list(self) -> None:
        res = self.client.get(MOVIES_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_auth_required_for_detail(self) -> None:
        movie = sample_movie()
        res = self.client.get(detail_url(movie.id))
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateMovieViewSetTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(email="user@example.com", password="testpass123")
        jwt_auth(self.client, "user@example.com", "testpass123")

    def test_list_movies_success(self) -> None:
        sample_movie(title="Alpha")
        sample_movie(title="Beta")
        res = self.client.get(MOVIES_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIsInstance(res.data, list)
        self.assertGreaterEqual(len(res.data), 2)
        self.assertIn("id", res.data[0])
        self.assertIn("title", res.data[0])
        self.assertIn("genres", res.data[0])
        self.assertIn("actors", res.data[0])
        self.assertIn("image", res.data[0])

    def test_retrieve_movie_success(self) -> None:
        movie = sample_movie("Detail")
        g1 = sample_genre("Drama")
        g2 = sample_genre("Fantasy")
        a1 = sample_actor("Emma", "Watson")
        a2 = sample_actor("Daniel", "Radcliffe")
        movie.genres.add(g1, g2)
        movie.actors.add(a1, a2)
        res = self.client.get(detail_url(movie.id))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIsInstance(res.data.get("genres"), list)
        self.assertIsInstance(res.data.get("actors"), list)
        self.assertIn("image", res.data)

    def test_filter_by_title_icontains(self) -> None:
        m1 = sample_movie(title="Liar Liar")
        m2 = sample_movie(title="Inception")
        res = self.client.get(MOVIES_URL, {"title": "liar"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        titles = [m["title"] for m in res.data]
        self.assertIn(m1.title, titles)
        self.assertNotIn(m2.title, titles)

    def test_filter_by_genres(self) -> None:
        g1 = sample_genre("Drama")
        g2 = sample_genre("Comedy")
        m1 = sample_movie(title="A")
        m2 = sample_movie(title="B")
        m1.genres.add(g1)
        m2.genres.add(g2)
        res = self.client.get(MOVIES_URL, {"genres": str(g1.id)})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        titles = [m["title"] for m in res.data]
        self.assertIn("A", titles)
        self.assertNotIn("B", titles)

    def test_filter_by_actors(self) -> None:
        a1 = sample_actor("Tom", "Hardy")
        a2 = sample_actor("Emma", "Stone")
        m1 = sample_movie(title="A")
        m2 = sample_movie(title="B")
        m1.actors.add(a1)
        m2.actors.add(a2)
        res = self.client.get(MOVIES_URL, {"actors": str(a1.id)})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        titles = [m["title"] for m in res.data]
        self.assertIn("A", titles)
        self.assertNotIn("B", titles)

    def test_non_admin_cannot_create_movie(self) -> None:
        payload = {"title": "New", "description": "Desc", "duration": 120, "genres": [], "actors": []}
        res = self.client.post(MOVIES_URL, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieViewSetTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.admin = get_user_model().objects.create_superuser(email="admin@example.com", password="adminpass123")
        jwt_auth(self.client, "admin@example.com", "adminpass123")

    def test_image_field_not_accepted_on_post(self) -> None:
        img_io = io.BytesIO()
        Image.new("RGB", (10, 10)).save(img_io, format="JPEG")
        img_io.seek(0)
        image = SimpleUploadedFile("bad.jpg", img_io.read(), content_type="image/jpeg")
        payload = {"title": "WithImage", "description": "X", "duration": 90, "genres": [], "actors": [], "image": image}
        res = self.client.post(MOVIES_URL, payload, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upload_image_success(self) -> None:
        movie = sample_movie("Pic")
        img_io = io.BytesIO()
        Image.new("RGB", (10, 10)).save(img_io, format="JPEG")
        img_io.seek(0)
        image = SimpleUploadedFile("ok.jpg", img_io.read(), content_type="image/jpeg")
        res = self.client.post(image_upload_url(movie.id), {"image": image}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)
