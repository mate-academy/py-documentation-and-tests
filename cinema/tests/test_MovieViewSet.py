import os
import tempfile

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework.reverse import reverse

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer

MOVIEVIEWSET_URL = reverse("cinema:movie-list")


def movie_sample(**params):
    defaults = {
        "title": "Fast & Furious 4",
        "description": "test description",
        "duration": 120,
    }
    defaults.update(params)
    return Movie.objects.create(**defaults)


def actor_sample(**params):
    defaults = {
        "first_name": "test first",
        "last_name": "test last",
    }
    defaults.update(params)
    return Actor.objects.create(**defaults)


def genre_sample(**params):
    defaults = {
        "name": "Test genre",
    }
    defaults.update(params)
    return Genre.objects.create(**defaults)


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


def image_upload_url(movie_id):
    return reverse("cinema:movie-upload-image", args=[movie_id])


class UnauthenticatedMovieViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required_on_movie_list(self):
        res = self.client.get(MOVIEVIEWSET_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_auth_required_on_upload_image(self):
        movie = movie_sample()

        res = self.client.post(image_upload_url(movie.id), {})

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test123@gmail.com",
            password="test132228",
        )
        self.client.force_authenticate(self.user)

    def test_list_movie(self):
        movie1 = movie_sample()
        movie2 = movie_sample(title="test1")
        movie3 = movie_sample(title="test2")
        movie4 = movie_sample(title="test3")
        movie5 = movie_sample(title="test4")
        movies = [movie1, movie2, movie3, movie4, movie5]
        res = self.client.get(MOVIEVIEWSET_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        for movie in movies:
            self.assertIn(MovieListSerializer(movie).data, res.data)

    def test_post_movie_forbidden(self):
        payload = {
            "title": "test title",
            "description": "test description",
            "duration": 200,
        }

        res = self.client.post(MOVIEVIEWSET_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_put_patch_delete_on_movie_forbidden(self):
        movie = movie_sample()
        url = detail_url(movie.id)

        for method in ("put", "patch", "delete"):
            with self.subTest(method=method):
                res = getattr(self.client, method)(url)

                self.assertEqual(
                    res.status_code, status.HTTP_403_FORBIDDEN
                )

    def test_filter_movies_by_titles(self):
        movie1 = movie_sample()
        movie2 = movie_sample(title="Herrica")
        movie3 = movie_sample(title="Harry Potter")

        res = self.client.get(MOVIEVIEWSET_URL, {"title": "Furious"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(MovieListSerializer(movie1).data, res.data)
        self.assertNotIn(MovieListSerializer(movie2).data, res.data)
        self.assertNotIn(MovieListSerializer(movie3).data, res.data)

    def test_filter_movies_by_genres(self):
        movie1 = movie_sample()
        movie2 = movie_sample(title="Herrica")
        movie3 = movie_sample(title="Harry Potter")

        genres1 = genre_sample(name="Fantasy")
        genres2 = genre_sample(name="Horror")
        genres3 = genre_sample(name="Historical")

        movie1.genres.add(genres1)
        movie2.genres.add(genres2)
        movie3.genres.add(genres3)

        res = self.client.get(
            MOVIEVIEWSET_URL,
            {"genres": f"{genres1.id},{genres3.id}"})

        res1 = self.client.get(
            MOVIEVIEWSET_URL,
            {"title": "Furious", "genres": f"{genres1.id},{genres3.id}"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(MovieListSerializer(movie1).data, res.data)
        self.assertNotIn(MovieListSerializer(movie2).data, res.data)
        self.assertIn(MovieListSerializer(movie3).data, res.data)

        self.assertEqual(res1.status_code, status.HTTP_200_OK)
        self.assertIn(MovieListSerializer(movie1).data, res1.data)
        self.assertNotIn(MovieListSerializer(movie2).data, res1.data)
        self.assertNotIn(MovieListSerializer(movie3).data, res1.data)

    def test_filter_movies_by_actors(self):
        movie1 = movie_sample()
        movie2 = movie_sample(title="Herrica")
        movie3 = movie_sample(title="Harry Potter")

        actor1 = actor_sample(first_name="Luna", last_name="Duhnovska")
        actor2 = actor_sample(first_name="Vovchik", last_name="Dubrovska")
        actor3 = actor_sample(first_name="Illiya", last_name="Duvolna")

        movie1.actors.add(actor1)
        movie2.actors.add(actor2)
        movie3.actors.add(actor3)

        res = self.client.get(
            MOVIEVIEWSET_URL,
            {"actors": f"{actor1.id},{actor3.id}"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(MovieListSerializer(movie1).data, res.data)
        self.assertNotIn(MovieListSerializer(movie2).data, res.data)
        self.assertIn(MovieListSerializer(movie3).data, res.data)

    def test_filter_movies_by_genres_returns_no_duplicates(self):
        movie = movie_sample()
        genre1 = genre_sample(name="Fantasy")
        genre2 = genre_sample(name="Horror")

        movie.genres.add(genre1, genre2)

        res = self.client.get(
            MOVIEVIEWSET_URL,
            {"genres": f"{genre1.id},{genre2.id}"},
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(
            res.data, MovieListSerializer([movie], many=True).data
        )

    def test_filter_movies_by_invalid_actors_returns_400(self):
        movie_sample()

        res = self.client.get(MOVIEVIEWSET_URL, {"actors": "1,xyz"})

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upload_image_forbidden(self):
        movie = movie_sample()

        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(
                image_upload_url(movie.id),
                {"image": ntf},
                format="multipart",
            )

        movie.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(movie.image)


class AdminMovieViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin007@gmail.com",
            password="1qaz3edc",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)

    def test_post_201_created(self):
        payload = {
            "title": "test title",
            "description": "test description",
            "duration": 200,
        }

        res = self.client.post(MOVIEVIEWSET_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_put_patch_delete_not_allowed(self):
        movie = movie_sample()
        url = detail_url(movie.id)

        for method in ("put", "patch", "delete"):
            with self.subTest(method=method):
                res = getattr(self.client, method)(url)

                self.assertEqual(
                    res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
                )

        self.assertTrue(Movie.objects.filter(id=movie.id).exists())

    def test_upload_image_to_movie(self):
        movie = movie_sample()
        url = image_upload_url(movie.id)

        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(url, {"image": ntf}, format="multipart")

        movie.refresh_from_db()
        self.addCleanup(movie.image.delete)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)
        self.assertTrue(os.path.exists(movie.image.path))

    def test_upload_invalid_image_bad_request(self):
        movie = movie_sample()

        res = self.client.post(
            image_upload_url(movie.id),
            {"image": "not an image"},
            format="multipart",
        )

        movie.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("image", res.data)
        self.assertFalse(movie.image)

    def test_get_on_upload_image_not_allowed(self):
        movie = movie_sample()

        res = self.client.get(image_upload_url(movie.id))

        self.assertEqual(
            res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED
        )
