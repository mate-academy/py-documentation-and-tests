from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from django.contrib.auth import get_user_model
from cinema.models import Movie, Genre, Actor

MOVIES_URL = reverse("cinema:movie-list")


def detail_url(movie_id):
    return reverse("cinema:movie-detail",
                   args=[movie_id])


def upload_url(movie_id):
    return reverse("cinema:movie-upload-image",
                   args=[movie_id])


User = get_user_model()


# ---------------------------
# PUBLIC (unauthenticated)
# ---------------------------
class PublicMoviesApiTests(APITestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIES_URL)
        self.assertEqual(res.status_code,
                         status.HTTP_401_UNAUTHORIZED)


# ---------------------------
# PRIVATE (authenticated user)
# ---------------------------
class PrivateMoviesApiTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="user@example.com",
            password="testpass"
        )
        self.client.force_authenticate(self.user)

    def test_list_movies_shows_image_url(self):
        Movie.objects.create(title="Liar",
                             description="d", duration=90)
        res = self.client.get(MOVIES_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data[0])

    def test_filter_by_title_genres_actors(self):
        g1 = Genre.objects.create(name="drama")
        a1 = Actor.objects.create(first_name="F", last_name="L")
        m1 = Movie.objects.create(title="Alpha",
                                  description="d", duration=90)
        m1.genres.add(g1)
        m1.actors.add(a1)

        Movie.objects.create(title="Beta", description="d", duration=90)

        url = f"{MOVIES_URL}?title=alp&genres={g1.id}&actors={a1.id}"
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["id"], m1.id)

    def test_retrieve_movie_shows_image(self):
        m = Movie.objects.create(title="Zed",
                                 description="d", duration=90)
        url = detail_url(m.id)
        res = self.client.get(url)
        self.assertEqual(res.status_code,
                         status.HTTP_200_OK)
        self.assertIn("image", res.data)

    def test_retrieve_nonexistent_movie_returns_404(self):
        url = detail_url(999999)
        res = self.client.get(url)
        self.assertEqual(res.status_code,
                         status.HTTP_404_NOT_FOUND)


# ---------------------------
# PERMISSIONS (authenticated non-admin)
# ---------------------------
class PrivateMoviesPermissionsTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="user@example.com", password="pass"
        )
        self.client.force_authenticate(self.user)

    def test_update_movie_forbidden_for_non_admin(self):
        m = Movie.objects.create(title="Old",
                                 description="d", duration=90)
        url = detail_url(m.id)
        res = self.client.patch(url, {"title": "Hack"})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_movie_forbidden_for_non_admin(self):
        m = Movie.objects.create(title="Keep",
                                 description="d", duration=90)
        url = detail_url(m.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code,
                         status.HTTP_403_FORBIDDEN)
        self.assertTrue(Movie.objects.filter(id=m.id).exists())


# ---------------------------
# ADMIN (superuser)
# ---------------------------
class AdminMoviesApiTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            email="admin@example.com", password="adminpass"
        )
        self.client.force_authenticate(self.admin)

    def test_admin_can_create_movie_but_no_image_field(self):
        payload = {
            "title": "New",
            "description": "d",
            "duration": 120,
        }
        res = self.client.post(MOVIES_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        movie = Movie.objects.get(id=res.data["id"])
        self.assertFalse(movie.image)
        self.assertIn(movie.image.name, (None, ""))

    def test_upload_image_endpoint_exists(self):
        m = Movie.objects.create(title="Pic",
                                 description="d", duration=90)
        url = upload_url(m.id)
        res = self.client.post(url, {})  # bad request without file
        self.assertIn(
            res.status_code,
            (status.HTTP_400_BAD_REQUEST,
             status.HTTP_415_UNSUPPORTED_MEDIA_TYPE),
        )

    def test_update_movie_as_admin(self):
        m = Movie.objects.create(title="Old",
                                 description="d", duration=90)
        url = detail_url(m.id)
        payload = {"title": "New title", "duration": 120}

        res = self.client.patch(url, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        m.refresh_from_db()
        self.assertEqual(m.title, "New title")
        self.assertEqual(m.duration, 120)

    def test_delete_movie_as_admin(self):
        m = Movie.objects.create(title="ToDelete",
                                 description="d", duration=90)
        url = detail_url(m.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Movie.objects.filter(id=m.id).exists())


# ---------------------------
# ADMIN – Validation errors
# ---------------------------
class AdminMoviesValidationTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            email="admin@example.com", password="adminpass"
        )
        self.client.force_authenticate(self.admin)

    def test_create_movie_invalid_payload_returns_400(self):
        payload = {
            "title": "",
            "description": "d",
            "duration": -5,
        }
        res = self.client.post(MOVIES_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("title", res.data)

    def test_update_movie_invalid_payload_returns_400(self):
        m = Movie.objects.create(title="Valid", description="d", duration=90)
        url = detail_url(m.id)
        # Викликаємо гарантовано невалідне через порожню назву
        res = self.client.patch(url, {"title": ""})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("title", res.data)
