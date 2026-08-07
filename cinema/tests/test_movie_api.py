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


def detail_url(movie_id):
    return reverse(
        "cinema:movie-detail",
        args=[movie_id],
    )


def image_upload_url(movie_id):
    return reverse(
        "cinema:movie-upload-image",
        args=[movie_id],
    )


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
    defaults = {
        "first_name": "George",
        "last_name": "Clooney",
    }
    defaults.update(params)

    return Actor.objects.create(**defaults)


class UnauthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(MOVIE_URL)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.user = get_user_model().objects.create_user(
            email="user@cinema.com",
            password="testpass123",
        )

        self.client.force_authenticate(self.user)

    def test_movies_list(self):
        first_movie = sample_movie(
            title="First movie",
        )
        second_movie = sample_movie(
            title="Second movie",
        )

        response = self.client.get(MOVIE_URL)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        returned_ids = {
            movie["id"]
            for movie in response.data
        }

        self.assertIn(first_movie.id, returned_ids)
        self.assertIn(second_movie.id, returned_ids)

    def test_retrieve_movie_detail(self):
        genre = sample_genre()
        actor = sample_actor()
        movie = sample_movie()

        movie.genres.add(genre)
        movie.actors.add(actor)

        response = self.client.get(
            detail_url(movie.id)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data["id"],
            movie.id,
        )
        self.assertEqual(
            response.data["title"],
            movie.title,
        )
        self.assertIn(
            "genres",
            response.data,
        )
        self.assertIn(
            "actors",
            response.data,
        )
        self.assertIn(
            "image",
            response.data,
        )

    def test_filter_movies_by_title(self):
        expected_movie = sample_movie(
            title="The Matrix",
        )
        sample_movie(
            title="Interstellar",
        )

        response = self.client.get(
            MOVIE_URL,
            {"title": "matrix"},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            len(response.data),
            1,
        )
        self.assertEqual(
            response.data[0]["id"],
            expected_movie.id,
        )

    def test_filter_movies_by_genres(self):
        drama = sample_genre(
            name="Drama",
        )
        comedy = sample_genre(
            name="Comedy",
        )

        drama_movie = sample_movie(
            title="Drama movie",
        )
        comedy_movie = sample_movie(
            title="Comedy movie",
        )

        drama_movie.genres.add(drama)
        comedy_movie.genres.add(comedy)

        response = self.client.get(
            MOVIE_URL,
            {"genres": str(drama.id)},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        returned_ids = [
            movie["id"]
            for movie in response.data
        ]

        self.assertIn(
            drama_movie.id,
            returned_ids,
        )
        self.assertNotIn(
            comedy_movie.id,
            returned_ids,
        )

    def test_filter_movies_by_multiple_genres(self):
        drama = sample_genre(
            name="Drama",
        )
        comedy = sample_genre(
            name="Comedy",
        )
        horror = sample_genre(
            name="Horror",
        )

        drama_movie = sample_movie(
            title="Drama movie",
        )
        comedy_movie = sample_movie(
            title="Comedy movie",
        )
        horror_movie = sample_movie(
            title="Horror movie",
        )

        drama_movie.genres.add(drama)
        comedy_movie.genres.add(comedy)
        horror_movie.genres.add(horror)

        response = self.client.get(
            MOVIE_URL,
            {
                "genres": f"{drama.id},{comedy.id}",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        returned_ids = [
            movie["id"]
            for movie in response.data
        ]

        self.assertIn(
            drama_movie.id,
            returned_ids,
        )
        self.assertIn(
            comedy_movie.id,
            returned_ids,
        )
        self.assertNotIn(
            horror_movie.id,
            returned_ids,
        )

    def test_filter_movies_by_actors(self):
        first_actor = sample_actor(
            first_name="Tom",
            last_name="Hanks",
        )
        second_actor = sample_actor(
            first_name="Brad",
            last_name="Pitt",
        )

        expected_movie = sample_movie(
            title="Expected movie",
        )
        other_movie = sample_movie(
            title="Other movie",
        )

        expected_movie.actors.add(first_actor)
        other_movie.actors.add(second_actor)

        response = self.client.get(
            MOVIE_URL,
            {"actors": str(first_actor.id)},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        returned_ids = [
            movie["id"]
            for movie in response.data
        ]

        self.assertIn(
            expected_movie.id,
            returned_ids,
        )
        self.assertNotIn(
            other_movie.id,
            returned_ids,
        )

    def test_regular_user_cannot_create_movie(self):
        genre = sample_genre()
        actor = sample_actor()

        payload = {
            "title": "New movie",
            "description": "New description",
            "duration": 120,
            "genres": [genre.id],
            "actors": [actor.id],
        }

        response = self.client.post(
            MOVIE_URL,
            payload,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertFalse(
            Movie.objects.filter(
                title=payload["title"]
            ).exists()
        )

    def test_regular_user_cannot_upload_image(self):
        movie = sample_movie()
        url = image_upload_url(movie.id)

        with tempfile.NamedTemporaryFile(
            suffix=".jpg"
        ) as image_file:
            image = Image.new(
                "RGB",
                (10, 10),
            )
            image.save(
                image_file,
                format="JPEG",
            )
            image_file.seek(0)

            response = self.client.post(
                url,
                {"image": image_file},
                format="multipart",
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )


class AdminMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.admin = (
            get_user_model()
            .objects
            .create_superuser(
                email="admin@cinema.com",
                password="testpass123",
            )
        )

        self.client.force_authenticate(self.admin)

        self.genre = sample_genre()
        self.actor = sample_actor()

    def test_admin_can_create_movie(self):
        payload = {
            "title": "New movie",
            "description": "New description",
            "duration": 120,
            "genres": [self.genre.id],
            "actors": [self.actor.id],
        }

        response = self.client.post(
            MOVIE_URL,
            payload,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        movie = Movie.objects.get(
            id=response.data["id"]
        )

        self.assertEqual(
            movie.title,
            payload["title"],
        )
        self.assertEqual(
            movie.description,
            payload["description"],
        )
        self.assertEqual(
            movie.duration,
            payload["duration"],
        )
        self.assertIn(
            self.genre,
            movie.genres.all(),
        )
        self.assertIn(
            self.actor,
            movie.actors.all(),
        )

    def test_image_is_ignored_when_creating_movie(self):
        with tempfile.NamedTemporaryFile(
            suffix=".jpg"
        ) as image_file:
            image = Image.new(
                "RGB",
                (10, 10),
            )
            image.save(
                image_file,
                format="JPEG",
            )
            image_file.seek(0)

            payload = {
                "title": "Movie with image",
                "description": "Description",
                "duration": 100,
                "genres": [self.genre.id],
                "actors": [self.actor.id],
                "image": image_file,
            }

            response = self.client.post(
                MOVIE_URL,
                payload,
                format="multipart",
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        movie = Movie.objects.get(
            id=response.data["id"]
        )

        self.assertFalse(movie.image)

    def test_upload_image_to_movie(self):
        movie = sample_movie()
        url = image_upload_url(movie.id)

        with tempfile.NamedTemporaryFile(
            suffix=".jpg"
        ) as image_file:
            image = Image.new(
                "RGB",
                (10, 10),
            )
            image.save(
                image_file,
                format="JPEG",
            )
            image_file.seek(0)

            response = self.client.post(
                url,
                {"image": image_file},
                format="multipart",
            )

        movie.refresh_from_db()

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertIn(
            "image",
            response.data,
        )
        self.assertTrue(movie.image)
        self.assertTrue(
            os.path.exists(movie.image.path)
        )

        movie.image.delete()

    def test_upload_invalid_image(self):
        movie = sample_movie()
        url = image_upload_url(movie.id)

        response = self.client.post(
            url,
            {"image": "not-an-image"},
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
