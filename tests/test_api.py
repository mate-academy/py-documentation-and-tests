import tempfile

from PIL import Image
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")


def movie_detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


def sample_movie(**params):
    defaults = {
        "title": "Test Movie",
        "description": "description",
        "duration": 120,
    }
    defaults.update(params)

    return Movie.objects.create(**defaults)


def sample_genre(**params):
    defaults = {
        "name": "Genre",
    }
    defaults.update(params)

    return Genre.objects.create(**defaults)


def sample_actor(**params):
    defaults = {"first_name": "Test", "last_name": "Actor"}
    defaults.update(params)

    return Actor.objects.create(**defaults)


class TestUnauthorizedMovieAPI(APITestCase):

    def setUp(self):
        self.movie = sample_movie()
        self.genre = sample_genre()
        self.actor = sample_actor()

    def test_movie_list(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_movie_detail(self):
        url = movie_detail_url(self.movie.id)
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_movie_create(self):
        payload = {
            "title": "Test Movie create",
            "description": "description",
            "duration": 200,
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(Movie.objects.count(), 1)

    def test_movie_put(self):
        url = movie_detail_url(self.movie.id)
        payload = {
            "title": "Test Movie create",
            "description": "description",
            "duration": 200,
        }
        res = self.client.post(url, payload)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(Movie.objects.count(), 1)

    def test_movie_patch(self):
        url = movie_detail_url(self.movie.id)
        payload = {
            "title": "Test Movie patch",
        }
        res = self.client.patch(url, payload)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(Movie.objects.count(), 1)
        self.assertNotEqual(self.movie.title, payload["title"])

    def test_movie_delete(self):
        url = movie_detail_url(self.movie.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(Movie.objects.count(), 1)


# noinspection PyUnresolvedReferences
class TestAuthorizedMovieAPI(APITestCase):

    def setUp(self):
        user = get_user_model().objects.create_user(
            email="user@user.com",
            password="userpassword",
        )
        self.client.force_authenticate(user)
        self.movie = sample_movie()
        self.genre = sample_genre()
        self.actor = sample_actor()

    def test_movie_list(self):
        res = self.client.get(MOVIE_URL)
        serializer = MovieListSerializer(Movie.objects.all(), many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_movie_list_with_filters(self):
        res = self.client.get(
            MOVIE_URL,
            {"title": "Test"}
        )
        serializer = MovieListSerializer(Movie.objects.all(), many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

        movie_genre = sample_movie()
        movie_genre.genres.add(self.genre)
        res = self.client.get(
            MOVIE_URL,
            {"genres": f"{self.genre.id}"}
        )
        serializer = MovieListSerializer([movie_genre], many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

        movie_actor = sample_movie()
        movie_actor.actors.add(self.actor)
        res = self.client.get(
            MOVIE_URL,
            {"actors": f"{self.actor.id}"}
        )
        serializer = MovieListSerializer([movie_actor], many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

        movie_all = sample_movie()
        movie_all.genres.add(self.genre)
        movie_all.actors.add(self.actor)

        res = self.client.get(
            MOVIE_URL,
            {
                "genres": f"{self.genre.id}",
                "actors": f"{self.actor.id}",
                "title": f"{self.movie.title}",
             }
        )
        serializer = MovieListSerializer([movie_all], many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

        res = self.client.get(
            MOVIE_URL,
        )
        serializer = MovieListSerializer(Movie.objects.all(), many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)
        self.assertEqual(len(res.data), 4)

    def test_movie_detail(self):
        url = movie_detail_url(self.movie.id)
        self.movie.genres.add(self.genre)
        self.movie.actors.add(self.actor)

        res = self.client.get(url)
        serializer = MovieDetailSerializer(self.movie)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_movie_create(self):
        payload = {
            "title": "Test Movie create",
            "description": "description",
            "duration": 200,
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Movie.objects.count(), 1)

    def test_movie_put(self):
        url = movie_detail_url(self.movie.id)
        payload = {
            "title": "Test Movie put",
            "description": "description",
            "duration": 200,
        }
        res = self.client.put(url, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Movie.objects.count(), 1)

    def test_movie_patch(self):
        url = movie_detail_url(self.movie.id)
        payload = {
            "title": "Test Movie patch",
        }
        res = self.client.patch(url, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Movie.objects.count(), 1)

    def test_movie_delete(self):
        url = movie_detail_url(self.movie.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Movie.objects.count(), 1)


class TestAdminMovieAPI(APITestCase):

    def setUp(self):
        admin = get_user_model().objects.create_user(
            email="admin@admin.com",
            password="admin_password",
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_authenticate(admin)
        self.movie = sample_movie()
        self.genre = sample_genre()
        self.actor = sample_actor()


    def test_movie_create(self):
        payload = {
            "title": "Test Movie create",
            "description": "description",
            "duration": 200,
            "genres": f"{self.genre.id}",
            "actors": f"{self.actor.id}",
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Movie.objects.count(), 2)

    def test_movie_put_not_allowed(self):
        url = movie_detail_url(self.movie.id)
        payload = {
            "title": "Test Movie put",
            "description": "description",
            "duration": 200,
            "genres": f"{self.genre.id}",
            "actors": f"{self.actor.id}",
        }
        res = self.client.put(url, payload)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(Movie.objects.count(), 1)

    def test_movie_patch_not_allowed(self):
        url = movie_detail_url(self.movie.id)
        payload = {
            "title": "Test Movie patch",
        }
        res = self.client.patch(url, payload)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(Movie.objects.count(), 1)

    def test_movie_delete_not_allowed(self):
        url = movie_detail_url(self.movie.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(Movie.objects.count(), 1)

    def test_movie_image_creation(self):
        url = reverse("cinema:movie-upload-image", args=[self.movie.id])
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(url, {"image": ntf}, format="multipart")
            self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.movie.refresh_from_db()
        url = movie_detail_url(self.movie.id)
        res = self.client.get(url)
        self.assertContains(res, self.movie.image.url)
        self.assertIsNotNone(res.data["image"])
        self.movie.image.delete()

