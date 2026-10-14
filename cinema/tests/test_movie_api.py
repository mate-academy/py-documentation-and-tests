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


class MovieViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "viewer@example.com", "password"
        )
        self.admin = get_user_model().objects.create_superuser(
            "admin@example.com", "password"
        )
        self.genre = sample_genre()
        self.other_genre = sample_genre(name="Comedy")
        self.actor = sample_actor()
        self.other_actor = sample_actor(
            first_name="Meryl", last_name="Streep"
        )
        self.movie = sample_movie(title="Ocean's Eleven")
        self.movie.genres.add(self.genre)
        self.movie.actors.add(self.actor)
        self.other_movie = sample_movie(title="The Devil Wears Prada")
        self.other_movie.genres.add(self.other_genre)
        self.other_movie.actors.add(self.other_actor)

    def test_list_movies_requires_authentication(self):
        response = self.client.get(MOVIE_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_movies_returns_simplified_movie_data(self):
        self.client.force_authenticate(self.user)

        response = self.client.get(MOVIE_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        movie_data = next(
            item for item in response.data if item["id"] == self.movie.id
        )
        self.assertEqual(movie_data["genres"], [self.genre.name])
        self.assertEqual(movie_data["actors"], [self.actor.full_name])
        self.assertEqual(
            set(movie_data),
            {"id", "title", "description", "duration", "genres", "actors", "image"},
        )

    def test_retrieve_movie_returns_nested_data(self):
        self.client.force_authenticate(self.user)

        response = self.client.get(detail_url(self.movie.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], self.movie.title)
        self.assertEqual(response.data["genres"], [{"id": self.genre.id, "name": self.genre.name}])
        self.assertEqual(response.data["actors"][0]["full_name"], self.actor.full_name)

    def test_retrieve_nonexistent_movie_returns_not_found(self):
        self.client.force_authenticate(self.user)

        response = self.client.get(detail_url(9999))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_movie_requires_admin(self):
        self.client.force_authenticate(self.user)

        response = self.client.post(MOVIE_URL, {})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_create_movie_with_genres_and_actors(self):
        self.client.force_authenticate(self.admin)
        payload = {
            "title": "New movie",
            "description": "A description",
            "duration": 110,
            "genres": [self.genre.id],
            "actors": [self.actor.id],
        }

        response = self.client.post(MOVIE_URL, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(title="New movie")
        self.assertEqual(list(movie.genres.all()), [self.genre])
        self.assertEqual(list(movie.actors.all()), [self.actor])

    def test_create_movie_with_invalid_related_ids_returns_bad_request(self):
        self.client.force_authenticate(self.admin)
        payload = {
            "title": "Invalid movie",
            "description": "A description",
            "duration": 110,
            "genres": [9999],
            "actors": [self.actor.id],
        }

        response = self.client.post(MOVIE_URL, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Movie.objects.filter(title="Invalid movie").exists())

    def test_filter_movies_by_title_genres_and_actors(self):
        self.client.force_authenticate(self.user)
        cases = (
            ({"title": "ocean"}, [self.movie.id]),
            ({"genres": str(self.genre.id)}, [self.movie.id]),
            ({"actors": str(self.other_actor.id)}, [self.other_movie.id]),
            (
                {"genres": f"{self.genre.id},{self.other_genre.id}"},
                [self.movie.id, self.other_movie.id],
            ),
            (
                {"genres": str(self.genre.id), "actors": str(self.other_actor.id)},
                [],
            ),
        )

        for params, expected_ids in cases:
            with self.subTest(params=params):
                response = self.client.get(MOVIE_URL, params)
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(
                    {item["id"] for item in response.data}, set(expected_ids)
                )

    def test_upload_image_requires_admin(self):
        self.client.force_authenticate(self.user)

        response = self.client.post(
            image_upload_url(self.movie.id), {"image": "not-image"}
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


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
