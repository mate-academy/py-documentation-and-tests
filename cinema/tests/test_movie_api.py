import tempfile
import os
from typing import List

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
    cinema_hall = CinemaHall.objects.create(name="Blue", rows=20,
                                            seats_in_row=20)

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
            res = self.client.post(
                url, {"image": ntf}, format="multipart"
            )
        self.movie.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)
        self.assertTrue(os.path.exists(self.movie.image.path))

    def test_upload_image_bad_request(self):
        """Test uploading an invalid image"""
        url = image_upload_url(self.movie.id)
        res = self.client.post(
            url, {"image": "not image"}, format="multipart"
        )

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

    def test_list_movies(self):
        data_movie = defaults = {
            "title": "Sample movie 2",
            "description": "Sample description ",
            "duration": 90,
        }
        simple_movie_2 = sample_movie(**data_movie)

        response = self.client.get(reverse("cinema:movie-list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)
        self.assertEqual(response.data, serializer.data)

    def test_retrieve_movie(self):
        response = self.client.get(
            reverse("cinema:movie-detail", args=[self.movie.id])
        )
        self.assertEqual(response.status_code, 200)

        movie = Movie.objects.get(id=self.movie.id)
        serializer = MovieDetailSerializer(movie)

        self.assertEqual(response.data, serializer.data)

    def test_filter_movies_by_title(self):
        response = self.client.get(
            reverse("cinema:movie-list") + "?title=Sample movie"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.movie.id)

    def test_filter_movies_by_genres(self):
        self.movie.genres.add(self.genre)
        response = self.client.get(
            reverse("cinema:movie-list") + f"?genres={self.genre.id}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.movie.id)

    def test_filter_movies_by_actors(self):
        self.movie.actors.add(self.actor)
        response = self.client.get(
            reverse("cinema:movie-list") + f"?actors={self.actor.id}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.movie.id)

    def test_create_movie(self):
        actor2_data = {"first_name": "Alex", "last_name": "Blue"}
        actor_2 = sample_actor(**actor2_data)
        payload = {
            "title": "Movie Three",
            "description": "Sample description",
            "duration": 100,
            "genres": [self.genre.id],
            "actors": [self.actor.id, actor_2.id]
        }
        response = self.client.post(
            reverse("cinema:movie-list"), data=payload
        )
        self.assertEqual(response.status_code, 201)

        movies = Movie.objects.all()
        self.assertEqual(len(movies), 2)

        movie = Movie.objects.get(id=response.data["id"])

        self.assertEqual(movie.title, payload["title"])
        self.assertEqual(movie.duration, payload["duration"])
        self.assertEqual(list(movie.genres.all()), [self.genre])
        self.assertEqual(
            list(movie.actors.all()), [self.actor, actor_2]
        )

    def test_permission(self):
        self.user.is_staff = False
        self.user.save()

        response = self.client.get(reverse("cinema:movie-list"))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(
            reverse("cinema:movie-detail", args=[self.movie.id])
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            reverse("cinema:movie-list"), data={}
        )
        self.assertEqual(response.status_code, 403)

        self.client.logout()

        response = self.client.get(reverse("cinema:movie-list"))
        self.assertEqual(response.status_code, 401)

        response = self.client.get(
            reverse("cinema:movie-detail", args=[self.movie.id])
        )
        self.assertEqual(response.status_code, 401)

        response = self.client.post(
            reverse("cinema:movie-list"), data={}
        )
        self.assertEqual(response.status_code, 401)
