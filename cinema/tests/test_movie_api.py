import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer


MOVIE_URL = reverse("cinema:movie-list")


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


def image_upload_url(movie_id):
    return reverse("cinema:movie-upload-image", args=[movie_id])


def sample_genre(**params):
    defaults = {"name": "Comedy"}
    defaults.update(params)
    return Genre.objects.create(**defaults)


def sample_actor(**params):
    defaults = {"first_name": "Test", "last_name": "Actor"}
    defaults.update(params)
    return Actor.objects.create(**defaults)


def sample_movie(**params):
    defaults = {
        "title": "Sample Movie",
        "description": "A great sample movie.",
        "duration": 120,
    }
    defaults.update(params)
    movie = Movie.objects.create(**defaults)

    if "genres_data" in params:
        for genre_data in params["genres_data"]:
            movie.genres.add(sample_genre(**genre_data))
    if "actors_data" in params:
        for actor_data in params["actors_data"]:
            movie.actors.add(sample_actor(**actor_data))
    return movie


class PublicMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required_for_list(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_auth_required_for_detail(self):
        movie = sample_movie()
        url = detail_url(movie.id)
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@example.com", "testpass123"
        )
        self.client.force_authenticate(self.user)

    def test_list_movies_paginated(self):
        sample_movie(title="Movie 1")
        sample_movie(title="Movie 2")
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("results", res.data)
        self.assertIn("count", res.data)

        movies = Movie.objects.all().order_by("title")
        serializer = MovieListSerializer(movies, many=True)
        self.assertEqual(len(res.data["results"]), movies.count())
        if movies.count() <= 10:
            self.assertEqual(res.data["results"], serializer.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        movie.genres.add(sample_genre(name="Action"))
        movie.actors.add(sample_actor(first_name="John"))

        url = detail_url(movie.id)
        res = self.client.get(url)
        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_title(self):
        sample_movie(title="Alpha Movie")
        movie2 = sample_movie(title="Beta Test Movie")
        sample_movie(title="Gamma Film")

        res = self.client.get(MOVIE_URL, {"title": "Test"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 1)
        self.assertEqual(res.data["results"][0]["title"], movie2.title)

    def test_filter_movies_by_genres(self):
        genre1 = sample_genre(name="Sci-Fi")
        genre2 = sample_genre(name="Fantasy")
        movie1 = sample_movie(title="Movie Sci-Fi")
        movie1.genres.add(genre1)
        movie2 = sample_movie(title="Movie Fantasy")
        movie2.genres.add(genre2)
        movie3 = sample_movie(title="Movie Both")
        movie3.genres.add(genre1, genre2)

        res = self.client.get(MOVIE_URL, {"genres": f"{genre1.id}"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 2)
        titles = sorted([m["title"] for m in res.data["results"]])
        self.assertEqual(titles, sorted([movie1.title, movie3.title]))

    def test_filter_movies_by_actors(self):
        actor1 = sample_actor(first_name="ActorA")
        actor2 = sample_actor(first_name="ActorB")
        movie1 = sample_movie(title="Movie ActorA")
        movie1.actors.add(actor1)
        movie2 = sample_movie(title="Movie ActorB")
        movie2.actors.add(actor2)
        movie3 = sample_movie(title="Movie Both Actors")
        movie3.actors.add(actor1, actor2)

        res = self.client.get(MOVIE_URL, {"actors": f"{actor1.id}"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 2)
        titles = sorted([m["title"] for m in res.data["results"]])
        self.assertEqual(titles, sorted([movie1.title, movie3.title]))

    def test_create_movie_forbidden(self):
        payload = {
            "title": "New Movie", "description": "Desc", "duration": 100
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_upload_image_forbidden(self):
        movie = sample_movie()
        url = image_upload_url(movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(url, {"image": ntf},
                                   format="multipart")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_user = get_user_model().objects.create_superuser(
            "admin@example.com", "adminpass123"
        )
        self.client.force_authenticate(self.admin_user)
        self.genre1 = sample_genre(name="Action")
        self.actor1 = sample_actor(first_name="AdminActor")

    def test_create_movie(self):
        payload = {
            "title": "Admin Movie",
            "description": "Admin Desc",
            "duration": 95,
            "genres": [self.genre1.id],
            "actors": [self.actor1.id],
        }
        res = self.client.post(MOVIE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(id=res.data["id"])
        for key in ["title", "description", "duration"]:
            self.assertEqual(payload[key], getattr(movie, key))
        self.assertIn(self.genre1, movie.genres.all())
        self.assertIn(self.actor1, movie.actors.all())

    def test_upload_image_to_movie(self):
        movie = sample_movie()
        url = image_upload_url(movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(url, {"image": ntf}, format="multipart")
        movie.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)
        self.assertTrue(os.path.exists(movie.image.path))
        if movie.image:
            movie.image.delete()

    def test_upload_image_bad_request(self):
        movie = sample_movie()
        url = image_upload_url(movie.id)
        res = self.client.post(url, {"image": "not image"},
                               format="multipart")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_image_field_ignored_on_movie_create(self):
        url = MOVIE_URL
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            payload = {
                "title": "Title With Image Attempt",
                "description": "Description",
                "duration": 90,
                "genres": [self.genre1.id],
                "actors": [self.actor1.id],
                "image": ntf,
            }
            res = self.client.post(url, payload, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(title="Title With Image Attempt")
        self.assertFalse(movie.image)

    def test_image_url_shown_on_movie_detail_if_uploaded(self):
        movie = sample_movie()
        upload_url_path = image_upload_url(movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(
                upload_url_path, {"image": ntf}, format="multipart"
            )

        res = self.client.get(detail_url(movie.id))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)
        self.assertIsNotNone(res.data["image"])
        if movie.image:
            movie.image.delete()

    def test_image_url_shown_on_movie_list_if_uploaded(self):
        movie = sample_movie()
        upload_url_path = image_upload_url(movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(
                upload_url_path, {"image": ntf}, format="multipart"
            )

        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data["results"][0].keys())
        self.assertIsNotNone(res.data["results"][0]["image"])
        if movie.image:
            movie.image.delete()
