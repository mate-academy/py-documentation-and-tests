from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from cinema.models import Actor, Genre, Movie

MOVIE_LIST_URL = reverse("cinema:movie-list")


def movie_detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


def movie_upload_image_url(movie_id):
    return reverse("cinema:movie-upload-image", args=[movie_id])


class MovieViewSetUnauthenticatedTests(APITestCase):
    """Anonymous user"""

    def test_list_requires_authentication(self):
        res = self.client.get(MOVIE_LIST_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_requires_authentication(self):
        res = self.client.post(MOVIE_LIST_URL, {})

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class MovieViewSetUserTests(APITestCase):
    """Regular user"""

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            email="user@test.com",
            password="testpass123",
        )

        cls.drama = Genre.objects.create(name="Drama")
        cls.comedy = Genre.objects.create(name="Comedy")
        cls.hanks = Actor.objects.create(first_name="Tom", last_name="Hanks")
        cls.depp = Actor.objects.create(first_name="Johnny", last_name="Depp")

        cls.movie1 = Movie.objects.create(
            title="The Green Mile",
            description="Prison drama",
            duration=189,
        )
        cls.movie1.genres.add(cls.drama)
        cls.movie1.actors.add(cls.hanks)

        cls.movie2 = Movie.objects.create(
            title="Comedy Show",
            description="Funny movie",
            duration=95,
        )
        cls.movie2.genres.add(cls.comedy)
        cls.movie2.actors.add(cls.depp)

    def setUp(self):
        self.client.force_authenticate(user=self.user)

    def test_list_movies(self):
        res = self.client.get(MOVIE_LIST_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)

    def test_list_uses_slug_fields_for_genres_and_actors(self):
        res = self.client.get(MOVIE_LIST_URL)

        movie = next(m for m in res.data if m["title"] == "The Green Mile")
        self.assertEqual(movie["genres"], ["Drama"])
        self.assertEqual(movie["actors"], ["Tom Hanks"])

    def test_filter_by_title(self):
        res = self.client.get(MOVIE_LIST_URL, {"title": "green"})

        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], "The Green Mile")

    def test_filter_by_genres(self):
        res = self.client.get(MOVIE_LIST_URL, {"genres": str(self.drama.id)})

        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], "The Green Mile")

    def test_filter_by_actors(self):
        res = self.client.get(MOVIE_LIST_URL, {"actors": str(self.depp.id)})

        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], "Comedy Show")

    def test_retrieve_movie_uses_detail_serializer(self):
        res = self.client.get(movie_detail_url(self.movie1.id))

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["title"], "The Green Mile")
        self.assertEqual(res.data["genres"][0]["name"], "Drama")
        self.assertEqual(res.data["actors"][0]["full_name"], "Tom Hanks")

    def test_user_cannot_create_movie(self):
        payload = {
            "title": "New Movie",
            "description": "Text",
            "duration": 100,
            "genres": [self.drama.id],
            "actors": [self.hanks.id],
        }
        res = self.client.post(MOVIE_LIST_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Movie.objects.filter(title="New Movie").exists())

    def test_user_cannot_upload_image(self):
        res = self.client.post(movie_upload_image_url(self.movie1.id), {})

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class MovieViewSetAdminTests(APITestCase):
    """Admin"""

    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_superuser(
            email="admin@test.com",
            password="testpass123",
        )
        cls.drama = Genre.objects.create(name="Drama")
        cls.hanks = Actor.objects.create(first_name="Tom", last_name="Hanks")

    def setUp(self):
        self.client.force_authenticate(user=self.admin)

    def test_admin_can_create_movie(self):
        payload = {
            "title": "Test Movie",
            "description": "Text",
            "duration": 120,
            "genres": [self.drama.id],
            "actors": [self.hanks.id],
        }
        res = self.client.post(MOVIE_LIST_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(title="Admin Movie")
        self.assertEqual(movie.duration, 120)
        self.assertEqual(list(movie.genres.all()), [self.drama])
        self.assertEqual(list(movie.actors.all()), [self.hanks])

    def test_create_without_required_fields_fails(self):
        res = self.client.post(
            MOVIE_LIST_URL,
            {"title": "No duration"},
            format="json",
        )

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Movie.objects.filter(title="No duration").exists())
