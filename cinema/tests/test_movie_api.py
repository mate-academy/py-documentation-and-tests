import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

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
    cinema_hall = CinemaHall.objects.create(name="Blue", rows=20, seats_in_row=20)

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


class MovieViewSetTests(TestCase):
    def setUp(self):
        self.api_client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="testuser@example.com", password="testpassword123"
        )
        self.api_client.force_authenticate(self.user)
        self.movie_list_url = reverse("cinema:movie-list")

    def get_movie_detail_url(self, movie_id):
        return reverse("cinema:movie-detail", args=[movie_id])

    def get_movie_image_upload_url(self, movie_id):
        return reverse("cinema:movie-upload-image", args=[movie_id])

    def test_retrieve_movie_list(self):
        Movie.objects.create(title="First Movie", duration=120)
        Movie.objects.create(title="Second Movie", duration=120)

        response = self.api_client.get(self.movie_list_url)

        all_movies = Movie.objects.all()
        expected_data = MovieListSerializer(all_movies, many=True).data

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, expected_data)

    def test_retrieve_movie_list_with_genre_and_actor_filters(self):
        genre_action = Genre.objects.create(name="Action")
        genre_drama = Genre.objects.create(name="Drama")
        actor_alpha = Actor.objects.create(first_name="Alpha", last_name="Doe")
        actor_beta = Actor.objects.create(first_name="Beta", last_name="Actor")

        movie_action = Movie.objects.create(title="Action Movie", duration=120)
        movie_drama = Movie.objects.create(title="Drama Movie", duration=120)

        movie_action.genres.add(genre_action)
        movie_drama.genres.add(genre_drama)

        movie_action.actors.add(actor_alpha)
        movie_drama.actors.add(actor_beta)

        response_genre = self.api_client.get(
            self.movie_list_url, {"genres": str(genre_action.id)}
        )
        response_titles_genre = [item["title"] for item in response_genre.data]
        self.assertIn(movie_action.title, response_titles_genre)
        self.assertNotIn(movie_drama.title, response_titles_genre)

        response_actor = self.api_client.get(
            self.movie_list_url, {"actors": str(actor_beta.id)}
        )
        response_titles_actor = [item["title"] for item in response_actor.data]
        self.assertIn(movie_drama.title, response_titles_actor)
        self.assertNotIn(movie_action.title, response_titles_actor)

    def test_retrieve_movie_detail(self):
        movie = Movie.objects.create(title="Detailed Test Movie", duration=120)
        url = self.get_movie_detail_url(movie.id)

        response = self.api_client.get(url)
        expected_data = MovieDetailSerializer(movie).data

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, expected_data)

    def test_create_new_movie(self):
        Genre.objects.create(name="Action")
        Actor.objects.create(first_name="Alpha", last_name="Doe")
        self.user.is_staff = True
        self.user.save()
        new_movie_payload = {
            "title": "New Created Movie",
            "description": "A test description for the movie",
            "duration": 120,
            "genres": [
                1,
            ],
            "actors": [
                1,
            ],
        }
        response = self.api_client.post(self.movie_list_url, new_movie_payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Movie.objects.filter(title="New Created Movie").exists())

    def test_upload_image_requires_admin_permission(self):
        movie = Movie.objects.create(title="Image Upload Movie", duration=120)
        upload_url = self.get_movie_image_upload_url(movie.id)

        with tempfile.NamedTemporaryFile(suffix=".jpg") as image_file:
            image = Image.new("RGB", (100, 100))
            image.save(image_file, format="JPEG")
            image_file.seek(0)

            upload_payload = {
                "image": image_file,
            }
            response_non_admin = self.api_client.post(
                upload_url, upload_payload, format="multipart"
            )
            self.assertEqual(response_non_admin.status_code, status.HTTP_403_FORBIDDEN)

        self.user.is_staff = True
        self.user.save()

        with tempfile.NamedTemporaryFile(suffix=".jpg") as image_file:
            image = Image.new("RGB", (100, 100))
            image.save(image_file, format="JPEG")
            image_file.seek(0)

            upload_payload = {
                "image": image_file,
            }
            response_admin = self.api_client.post(
                upload_url, upload_payload, format="multipart"
            )
            self.assertEqual(response_admin.status_code, status.HTTP_200_OK)
