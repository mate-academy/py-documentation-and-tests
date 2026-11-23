import os
import tempfile
from PIL import Image

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor

MOVIES_LIST_URL = lambda: reverse("cinema:movie-list")
MOVIE_DETAIL_URL = lambda pk: reverse("cinema:movie-detail", args=[pk])
MOVIE_UPLOAD_IMAGE_URL = lambda pk: reverse("cinema:movie-upload-image", args=[pk])


def obtain_access_token(client: APIClient, username: str, password: str) -> str:
    url = reverse("token_obtain_pair")
    res = client.post(url, {"email": username, "password": password}, format="json")
    assert res.status_code == 200, f"Token obtain failed: {res.status_code} {res.data}"
    return res.data["access"]


def create_user(**params):
    defaults = {"email": "user@example.com", "password": "pass12345"}
    defaults.update(params)
    return get_user_model().objects.create_user(**defaults)


def create_admin(**params):
    user = create_user(**params)
    user.is_staff = True
    user.is_superuser = True
    user.save()
    return user


def create_genre(name="Action"):
    return Genre.objects.create(name=name)


def create_actor(first_name="Tom", last_name="Hardy"):
    return Actor.objects.create(first_name=first_name, last_name=last_name)


def create_movie(title="Sample", description="Desc", duration=120, genres=None, actors=None):
    movie = Movie.objects.create(title=title, description=description, duration=duration)
    if genres:
        movie.genres.set(genres)
    if actors:
        movie.actors.set(actors)
    return movie


def make_temp_jpeg_file():
    temp_file = tempfile.NamedTemporaryFile(suffix=".jpg")
    image = Image.new("RGB", (10, 10))
    image.save(temp_file, format="JPEG")
    temp_file.seek(0)
    return temp_file


class TestPublicMovieViewSet(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_unauthenticated_list_is_unauthorized(self):
        response = self.client.get(MOVIES_LIST_URL())
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))


class TestPrivateMovieViewSetReadOnly(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="u1", password="pass12345"
        )
        token = obtain_access_token(self.client, self.user.username or self.user.email, "pass12345")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_list_returns_slug_and_image_fields(self):
        genre1 = create_genre("Drama")
        genre2 = create_genre("Comedy")
        actor1 = create_actor("Kate", "Winslet")
        actor2 = create_actor("Leonardo", "DiCaprio")
        movie1 = create_movie("Titanic", "Ship", 195, [genre1, genre2], [actor1, actor2])
        movie2 = create_movie("Inception", "Dream", 148, [genre2], [actor2])

        response = self.client.get(MOVIES_LIST_URL())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        sample = response.data[0]
        self.assertIn("genres", sample)
        self.assertIsInstance(sample["genres"], list)
        self.assertIn("actors", sample)
        self.assertIsInstance(sample["actors"], list)
        self.assertIn("image", sample)

    def test_retrieve_returns_nested_and_image(self):
        genre = create_genre("Sci-Fi")
        actor = create_actor("Keanu", "Reeves")
        movie = create_movie("Matrix", "Neo", 136, [genre], [actor])

        response = self.client.get(MOVIE_DETAIL_URL(movie.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("genres", response.data)
        self.assertIsInstance(response.data["genres"], list)
        self.assertIn("actors", response.data)
        self.assertIsInstance(response.data["actors"], list)
        self.assertIn("image", response.data)

    def test_filter_by_title(self):
        create_movie(title="Harry Potter and the Stone", description="...", duration=120)
        create_movie(title="HARRY and something", description="...", duration=90)
        create_movie(title="Other movie", description="...", duration=80)

        response = self.client.get(MOVIES_LIST_URL(), {"title": "harry"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = sorted([movie["title"] for movie in response.data])
        self.assertEqual(titles, ["HARRY and something", "Harry Potter and the Stone"])

    def test_filter_by_genres(self):
        genre1 = create_genre("Action")
        genre2 = create_genre("Drama")
        movie1 = create_movie("A1", "d", 100, [genre1], [])
        movie2 = create_movie("D1", "d", 100, [genre2], [])
        movie3 = create_movie("Both", "d", 100, [genre1, genre2], [])

        response = self.client.get(MOVIES_LIST_URL(), {"genres": f"{genre1.id},{genre2.id}"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = sorted([movie["title"] for movie in response.data])
        self.assertEqual(titles, ["A1", "Both", "D1"])

    def test_filter_by_actors(self):
        actor1 = create_actor("Tom", "Hanks")
        actor2 = create_actor("Tom", "Cruise")
        movie1 = create_movie("Hanks only", "d", 100, [], [actor1])
        movie2 = create_movie("Cruise only", "d", 100, [], [actor2])
        movie3 = create_movie("Both", "d", 100, [], [actor1, actor2])

        response = self.client.get(MOVIES_LIST_URL(), {"actors": f"{actor1.id},{actor2.id}"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = sorted([movie["title"] for movie in response.data])
        self.assertEqual(titles, ["Both", "Cruise only", "Hanks only"])

    def test_filter_combined_title_and_genres_and_actors_distinct(self):
        genre = create_genre("G")
        actor = create_actor("A", "A")
        movie = create_movie("Target", "d", 111, [genre], [actor])
        create_movie("Target 2", "d", 111, [genre], [])
        create_movie("Other", "d", 111, [], [actor])

        response = self.client.get(
            MOVIES_LIST_URL(),
            {"title": "tar", "genres": str(genre.id), "actors": str(actor.id)},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = [item["title"] for item in response.data]
        self.assertEqual(titles, ["Target"])

    def test_non_admin_cannot_create(self):
        payload = {"title": "New film", "description": "desc", "duration": 123}
        response = self.client.post(MOVIES_LIST_URL(), payload)
        self.assertIn(response.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED))
        self.assertFalse(Movie.objects.filter(title="New film").exists())

    def test_non_admin_cannot_upload_image(self):
        movie = create_movie()
        upload_url = MOVIE_UPLOAD_IMAGE_URL(movie.id)
        with make_temp_jpeg_file() as temp_image:
            response = self.client.post(upload_url, {"image": temp_image}, format="multipart")
        self.assertIn(response.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED))
        movie.refresh_from_db()
        self.assertFalse(bool(movie.image))


class TestAdminMovieViewSet(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = get_user_model().objects.create_superuser(
            email="admin@admin.com", password="pass12345"
        )
        token = obtain_access_token(self.client, self.admin.username or self.admin.email, "pass12345")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_admin_can_create_movie_with_relations(self):
        genre1 = create_genre("G1")
        genre2 = create_genre("G2")
        actor1 = create_actor("A1", "L1")
        actor2 = create_actor("A2", "L2")
        payload = {
            "title": "Admin Film",
            "description": "desc",
            "duration": 140,
            "genres": [genre1.id, genre2.id],
            "actors": [actor1.id, actor2.id],
        }
        response = self.client.post(MOVIES_LIST_URL(), payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(id=response.data["id"])
        self.assertEqual(movie.title, "Admin Film")
        self.assertEqual(set(movie.genres.values_list("id", flat=True)), {genre1.id, genre2.id})
        self.assertEqual(set(movie.actors.values_list("id", flat=True)), {actor1.id, actor2.id})

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_admin_can_upload_image_and_list_detail_show_image(self):
        movie = create_movie("With image", "d", 100)
        upload_url = MOVIE_UPLOAD_IMAGE_URL(movie.id)
        with make_temp_jpeg_file() as temp_image:
            response = self.client.post(upload_url, {"image": temp_image}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        movie.refresh_from_db()
        self.assertTrue(bool(movie.image))
        list_response = self.client.get(MOVIES_LIST_URL())
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        found = next(item for item in list_response.data if item["id"] == movie.id)
        self.assertIn("image", found)
        self.assertTrue(bool(found["image"]))
        detail_response = self.client.get(MOVIE_DETAIL_URL(movie.id))
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertIn("image", detail_response.data)
        self.assertTrue(bool(detail_response.data["image"]))
        try:
            path = movie.image.path
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass
