from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient
from PIL import Image
import tempfile
from cinema.models import Movie, Actor, Genre
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

MOVIE_URL = reverse("cinema:movie-list")


def sample_movie(**params):
    defaults = {
        "title": "Test Movie",
        "description": "Some description",
        "duration": 120,
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)


def sample_genre(name="Action"):
    return Genre.objects.create(name=name)


def sample_actor(first_name="John", last_name="Doe"):
    return Actor.objects.create(first_name=first_name, last_name=last_name)


class UnauthenticateMovieApiTest(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticateMovieApiTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.test", password="testpassword"
        )
        token_res = self.client.post(
            reverse("user:token_obtain_pair"),  # <-- namespace "user:"
            {"email": "test@test.test", "password": "testpassword"},
        )
        self.assertEqual(token_res.status_code, status.HTTP_200_OK)
        token = token_res.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_movies_list(self):
        movie = sample_movie()
        movie.genres.add(sample_genre())
        movie.actors.add(sample_actor())

        res = self.client.get(MOVIE_URL)

        movies = Movie.objects.all().prefetch_related("genres", "actors").distinct()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_movie_filters_by_title(self):
        sample_movie(title="Inception")
        sample_movie(title="Star wars")

        res = self.client.get(MOVIE_URL, {"title": "Inception"})

        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], "Inception")

    def test_movie_filters_by_genres(self):
        genre1 = sample_genre(name="Action")
        genre2 = sample_genre(name="Science fiction")

        movie1 = sample_movie(title="Inception")
        movie2 = sample_movie(title="Star wars")

        movie1.genres.add(genre1)
        movie2.genres.add(genre2)

        res = self.client.get(MOVIE_URL, {"genres": f"{genre1.id}"})

        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], "Inception")

    def test_movie_filters_by_actors(self):
        movie1 = sample_movie(title="Inception")
        movie2 = sample_movie(title="Star wars")

        actor1 = sample_actor(first_name="Poul", last_name="Walker")
        actor2 = sample_actor(first_name="Jason", last_name="Statham")

        movie1.actors.add(actor1)
        movie2.actors.add(actor2)

        res = self.client.get(MOVIE_URL, {"actors": f"{actor1.id}"})

        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], "Inception")

    def test_retrieve_movie(self):
        movie = sample_movie()
        movie.genres.add(sample_genre())
        movie.actors.add(sample_actor())

        url = reverse("cinema:movie-detail", args=[movie.id])
        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_invalid_genres_param_raises_validation(self):
        res = self.client.get(MOVIE_URL, {"genres": "abc,xyz"})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


class MovieImageUploadTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            email="admin.user@cinema.com", password="1qazcde3"
        )
        self.user = get_user_model().objects.create_user(
            email="user@example.com", password="password123"
        )

        self.admin_client = APIClient()
        self.admin_client.force_authenticate(self.admin)

        self.user_client = APIClient()
        self.user_client.force_authenticate(self.user)

    def _make_image_file(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".jpg")
        Image.new("RGB", (200, 200)).save(tmp, format="JPEG")
        tmp.seek(0)
        return tmp

    def test_admin_can_upload_image(self):
        movie = sample_movie(title="With Image")
        url = reverse("cinema:movie-upload-image", args=[movie.id])
        with self._make_image_file() as img:
            res = self.admin_client.post(url, {"image": img}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_non_admin_cannot_upload_image(self):
        movie = sample_movie(title="No Image")
        url = reverse("cinema:movie-upload-image", args=[movie.id])
        with self._make_image_file() as img:
            res = self.user_client.post(url, {"image": img}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
