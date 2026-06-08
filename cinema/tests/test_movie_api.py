import os
import tempfile

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import Actor, Genre, Movie

MOVIE_URL = reverse("cinema:movie-list")


def sample_genre(**params):
    defaults = {"name": "Drama"}
    defaults.update(params)

    return Genre.objects.create(**defaults)


def sample_actor(**params):
    defaults = {"first_name": "Tom", "last_name": "Hanks"}
    defaults.update(params)

    return Actor.objects.create(**defaults)


def sample_movie(**params):
    genres = params.pop("genres", [])
    actors = params.pop("actors", [])
    defaults = {
        "title": "Sample movie",
        "description": "Sample description",
        "duration": 90,
    }
    defaults.update(params)

    movie = Movie.objects.create(**defaults)
    movie.genres.set(genres)
    movie.actors.set(actors)

    return movie


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


def image_upload_url(movie_id):
    return reverse("cinema:movie-upload-image", args=[movie_id])


class UnauthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user@cinema.com",
            password="testpass123",
        )
        self.client.force_authenticate(self.user)

    def test_list_movies(self):
        genre = sample_genre()
        actor = sample_actor()
        sample_movie(
            title="First movie",
            genres=[genre],
            actors=[actor],
        )
        sample_movie(title="Second movie")

        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)
        self.assertEqual(res.data[0]["title"], "First movie")
        self.assertEqual(res.data[0]["genres"], [genre.name])
        self.assertEqual(res.data[0]["actors"], [actor.full_name])
        self.assertEqual(res.data[1]["title"], "Second movie")

    def test_retrieve_movie_detail(self):
        genre = sample_genre()
        actor = sample_actor()
        movie = sample_movie(genres=[genre], actors=[actor])

        res = self.client.get(detail_url(movie.id))

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["title"], movie.title)
        self.assertEqual(res.data["genres"][0]["name"], genre.name)
        self.assertEqual(res.data["actors"][0]["full_name"], actor.full_name)

    def test_filter_movies_by_title(self):
        sample_movie(title="The Green Mile")
        sample_movie(title="Shrek")

        res = self.client.get(MOVIE_URL, {"title": "green"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], "The Green Mile")

    def test_filter_movies_by_genres(self):
        genre1 = sample_genre(name="Drama")
        genre2 = sample_genre(name="Comedy")
        movie1 = sample_movie(title="Movie 1", genres=[genre1])
        movie2 = sample_movie(title="Movie 2", genres=[genre2])

        res = self.client.get(MOVIE_URL, {"genres": str(genre1.id)})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual([movie["id"] for movie in res.data], [movie1.id])
        self.assertNotIn(movie2.id, [movie["id"] for movie in res.data])

    def test_filter_movies_by_actors(self):
        actor1 = sample_actor(first_name="Keanu", last_name="Reeves")
        actor2 = sample_actor(first_name="Sandra", last_name="Bullock")
        movie1 = sample_movie(title="Movie 1", actors=[actor1])
        movie2 = sample_movie(title="Movie 2", actors=[actor2])

        res = self.client.get(MOVIE_URL, {"actors": str(actor1.id)})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual([movie["id"] for movie in res.data], [movie1.id])
        self.assertNotIn(movie2.id, [movie["id"] for movie in res.data])

    def test_create_movie_forbidden_for_non_admin(self):
        genre = sample_genre()
        actor = sample_actor()
        payload = {
            "title": "New movie",
            "description": "Description",
            "duration": 110,
            "genres": [genre.id],
            "actors": [actor.id],
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_upload_image_forbidden_for_non_admin(self):
        movie = sample_movie()

        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(
                image_upload_url(movie.id),
                {"image": ntf},
                format="multipart",
            )

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            email="admin@cinema.com",
            password="testpass123",
        )
        self.client.force_authenticate(self.user)
        self.movie = sample_movie()

    def tearDown(self):
        self.movie.image.delete()

    def test_create_movie(self):
        genre = sample_genre()
        actor = sample_actor()
        payload = {
            "title": "Interstellar",
            "description": "Space movie",
            "duration": 169,
            "genres": [genre.id],
            "actors": [actor.id],
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(id=res.data["id"])
        self.assertEqual(movie.title, payload["title"])
        self.assertEqual(movie.genres.first(), genre)
        self.assertEqual(movie.actors.first(), actor)

    def test_upload_image_to_movie(self):
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(
                image_upload_url(self.movie.id),
                {"image": ntf},
                format="multipart",
            )
        self.movie.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)
        self.assertTrue(os.path.exists(self.movie.image.path))

    def test_upload_image_bad_request(self):
        res = self.client.post(
            image_upload_url(self.movie.id),
            {"image": "not image"},
            format="multipart",
        )

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_image_to_movie_list(self):
        genre = sample_genre()
        actor = sample_actor()

        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(
                MOVIE_URL,
                {
                    "title": "Title",
                    "description": "Description",
                    "duration": 90,
                    "genres": [genre.id],
                    "actors": [actor.id],
                    "image": ntf,
                },
                format="multipart",
            )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(title="Title")
        self.assertFalse(movie.image)

    def test_image_url_is_shown_on_movie_detail(self):
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(
                image_upload_url(self.movie.id),
                {"image": ntf},
                format="multipart",
            )

        res = self.client.get(detail_url(self.movie.id))

        self.assertIn("image", res.data)

    def test_image_url_is_shown_on_movie_list(self):
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(
                image_upload_url(self.movie.id),
                {"image": ntf},
                format="multipart",
            )

        res = self.client.get(MOVIE_URL)

        self.assertIn("image", res.data[0])
