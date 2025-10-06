import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor

MOVIE_URL = reverse("cinema:movie-list")
MOVIE_SESSION_URL = reverse("cinema:moviesession-list")


def sample_movie(**params):
    defaults = {
        "title": "Sample movie",
        "description": "Sample description",
        "duration": 90,
    }
    defaults.update(params)

    return Movie.objects.create(**defaults)


def sample_genre(**params):
    defaults = {
        "name": "Drama",
    }
    defaults.update(params)

    return Genre.objects.create(**defaults)


def sample_actor(**params):
    defaults = {"first_name": "George", "last_name": "Clooney"}
    defaults.update(params)

    return Actor.objects.create(**defaults)


def sample_movie_session(**params):
    cinema_hall = CinemaHall.objects.create(
        name="Blue", rows=20, seats_in_row=20
    )

    defaults = {
        "show_time": "2022-06-02 14:00:00",
        "movie": None,
        "cinema_hall": cinema_hall,
    }
    defaults.update(params)

    return MovieSession.objects.create(**defaults)


def image_upload_url(movie_id):
    """Return URL for recipe image upload"""
    return reverse("cinema:movie-upload-image", args=[movie_id])


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


class MovieImageUploadTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)
        self.movie = sample_movie()
        self.genre = sample_genre()
        self.actor = sample_actor()
        self.movie_session = sample_movie_session(movie=self.movie)

    def tearDown(self):
        self.movie.image.delete()

    def test_upload_image_to_movie(self):
        """Test uploading an image to movie"""
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(url, {"image": ntf}, format="multipart")
        self.movie.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)
        self.assertTrue(os.path.exists(self.movie.image.path))

    def test_upload_image_bad_request(self):
        """Test uploading an invalid image"""
        url = image_upload_url(self.movie.id)
        res = self.client.post(url, {"image": "not image"}, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_image_to_movie_list(self):
        url = MOVIE_URL
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(
                url,
                {
                    "title": "Title",
                    "description": "Description",
                    "duration": 90,
                    "genres": [1],
                    "actors": [1],
                    "image": ntf,
                },
                format="multipart",
            )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(title="Title")
        self.assertFalse(movie.image)

    def test_image_url_is_shown_on_movie_detail(self):
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(detail_url(self.movie.id))

        self.assertIn("image", res.data)

    def test_image_url_is_shown_on_movie_list(self):
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(MOVIE_URL)

        self.assertIn("image", res.data[0].keys())

    def test_image_url_is_shown_on_movie_session_detail(self):
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(MOVIE_SESSION_URL)

        self.assertIn("movie_image", res.data[0].keys())


class MovieAuthTests(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class MovieViewSetTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.admin_user = get_user_model().objects.create_superuser(
            "admin2@example.com", "password"
        )
        self.user = get_user_model().objects.create_user(
            "user@example.com", "password123"
        )

        self.genre1 = sample_genre(name="Action")
        self.genre2 = sample_genre(name="Comedy")
        self.actor1 = sample_actor(first_name="Tom", last_name="Hanks")
        self.actor2 = sample_actor(first_name="Jim", last_name="Carrey")

        self.movie1 = sample_movie(title="Forrest Gump")
        self.movie1.genres.add(self.genre1)
        self.movie1.actors.add(self.actor1)

        self.movie2 = sample_movie(title="The Mask")
        self.movie2.genres.add(self.genre2)
        self.movie2.actors.add(self.actor2)

    def test_authenticated_user_can_read(self):
        self.client.force_authenticate(self.user)
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("title", res.data[0])

    def test_non_admin_cannot_create_movie(self):
        self.client.force_authenticate(self.user)
        payload = {"title": "New Movie", "description": "Desc", "duration": 100}
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_create_movie(self):
        self.client.force_authenticate(self.admin_user)
        payload = {
            "title": "New Movie",
            "description": "Desc",
            "duration": 100,
            "genres": [self.genre1.id],
            "actors": [self.actor1.id],
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(title="New Movie")
        self.assertIn(self.genre1, movie.genres.all())
        self.assertIn(self.actor1, movie.actors.all())

    def test_filter_movies_by_title(self):
        self.client.force_authenticate(self.user)
        res = self.client.get(MOVIE_URL, {"title": "forrest"})
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], "Forrest Gump")

    def test_filter_movies_by_genre(self):
        self.client.force_authenticate(self.user)
        res = self.client.get(MOVIE_URL, {"genres": str(self.genre2.id)})
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], "The Mask")

    def test_filter_movies_by_actor(self):
        self.client.force_authenticate(self.user)
        res = self.client.get(MOVIE_URL, {"actors": str(self.actor1.id)})
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], "Forrest Gump")

    def test_filter_movies_returns_distinct(self):
        self.client.force_authenticate(self.user)
        self.movie1.genres.add(self.genre2)
        res = self.client.get(MOVIE_URL, {"genres": f"{self.genre1.id},{self.genre2.id}"})
        titles = [m["title"] for m in res.data]
        self.assertEqual(len(titles), len(set(titles)))

    def test_get_serializer_class_list(self):
        from cinema.views import MovieViewSet
        view = MovieViewSet()
        view.action = "list"
        from cinema.serializers import MovieListSerializer
        self.assertEqual(view.get_serializer_class(), MovieListSerializer)

    def test_get_serializer_class_retrieve(self):
        from cinema.views import MovieViewSet
        view = MovieViewSet()
        view.action = "retrieve"
        from cinema.serializers import MovieDetailSerializer
        self.assertEqual(view.get_serializer_class(), MovieDetailSerializer)

    def test_get_serializer_class_upload_image(self):
        from cinema.views import MovieViewSet
        view = MovieViewSet()
        view.action = "upload_image"
        from cinema.serializers import MovieImageSerializer
        self.assertEqual(view.get_serializer_class(), MovieImageSerializer)

    def test_get_serializer_class_default(self):
        from cinema.views import MovieViewSet
        view = MovieViewSet()
        view.action = "create"
        from cinema.serializers import MovieSerializer
        self.assertEqual(view.get_serializer_class(), MovieSerializer)

