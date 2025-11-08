import os
import tempfile
from PIL import Image
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from django.test import TestCase
from rest_framework.reverse import reverse

from cinema.models import Movie, Genre, Actor

MOVIES_URL = reverse("cinema:movie-list")


def sample_genre(name="Comedy"):
    return Genre.objects.create(name=name)

def sample_actor(first_name="Tom", last_name="Hanks"):
    return Actor.objects.create(first_name=first_name, last_name=last_name)

def sample_movie(**params):
    defaults = {
        "title": "Sample movie",
        "description": "Sample description",
        "duration": 90,
        "image": None,
    }
    defaults.update(params)

    return Movie.objects.create(**defaults)

def image_upload_url(movie_id):
    return reverse("cinema:movie-upload-image", args=[movie_id])


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


class UnauthenticatedMovieApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(MOVIES_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@gmail.com",
            "testpassword123"
        )
        self.client.force_authenticate(self.user)

    def test_auth_required(self):
        response = self.client.get(MOVIES_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_movie_list(self):
        movie1 = sample_movie(title="Matrix")
        movie2 = sample_movie(title="Inception")

        res = self.client.get(MOVIES_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)
        titles = [m["title"] for m in res.data]
        self.assertIn(movie1.title, titles)
        self.assertIn(movie2.title, titles)

    def test_filter_movies_by_genres(self):
        genre1 = sample_genre(name="Action")
        genre2 = sample_genre(name="Drama")

        movie1 = sample_movie(title="Die Hard")
        movie2 = sample_movie(title="The Notebook")
        movie1.genres.add(genre1)
        movie2.genres.add(genre2)

        res = self.client.get(MOVIES_URL, {"genres": f"{genre1.id}"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], movie1.title)

    def test_filter_movies_by_actors(self):
        actor1 = sample_actor(first_name="Keanu", last_name="Reeves")
        actor2 = sample_actor(first_name="Ryan", last_name="Gosling")

        movie1 = sample_movie(title="Matrix")
        movie2 = sample_movie(title="Drive")
        movie1.actors.add(actor1)
        movie2.actors.add(actor2)

        res = self.client.get(MOVIES_URL, {"actors": f"{actor1.id}"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], movie1.title)

    def test_filter_movies_by_title(self):
        movie1 = sample_movie(title="Interstellar")
        movie2 = sample_movie(title="Tenet")

        res = self.client.get(MOVIES_URL, {"title": "stell"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], movie1.title)

    def test_retrieve_movie_detail(self):
        genre = sample_genre()
        actor = sample_actor()
        movie = sample_movie(title="Titanic")
        movie.genres.add(genre)
        movie.actors.add(actor)

        url = detail_url(movie.id)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["title"], movie.title)
        self.assertEqual(res.data["genres"][0]["name"], genre.name)
        self.assertEqual(res.data["actors"][0]["full_name"], actor.full_name)


class AdminMovieApiTests(APITestCase):

    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            email="admin@example.com", password="adminpass123"
        )
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def test_admin_can_create_movie(self):
        genre1 = sample_genre(name="Comedy")
        actor1 = sample_actor(first_name="Jim", last_name="Carrey")

        payload = {
            "title": "The Mask",
            "description": "Funny movie",
            "duration": 101,
            "genres": [genre1.id],
            "actors": [actor1.id],
        }

        res = self.client.post(MOVIES_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(id=res.data["id"])
        self.assertEqual(movie.title, payload["title"])
        self.assertIn(genre1, movie.genres.all())
        self.assertIn(actor1, movie.actors.all())

    def test_non_admin_cannot_create_movie(self):
        user = get_user_model().objects.create_user(
            email="regular@example.com", password="userpass123"
        )
        client = APIClient()
        client.force_authenticate(user)

        payload = {"title": "Should Fail", "description": "Nope", "duration": 100}
        res = client.post(MOVIES_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_upload_image_to_movie(self):
        movie = sample_movie()
        url = image_upload_url(movie.id)

        with tempfile.NamedTemporaryFile(suffix=".jpg") as image_file:
            img = Image.new("RGB", (10, 10))
            img.save(image_file, format="JPEG")
            image_file.seek(0)

            res = self.client.post(url, {"image": image_file}, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        movie.refresh_from_db()
        self.assertTrue(os.path.exists(movie.image.path))

        # Clean up created image file
        movie.image.delete(save=False)

    def test_upload_image_invalid(self):
        """Test uploading invalid image returns error"""
        movie = sample_movie()
        url = image_upload_url(movie.id)
        res = self.client.post(url, {"image": "notanimage"}, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)