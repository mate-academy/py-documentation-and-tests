from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from cinema.serializers import MovieListSerializer, MovieDetailSerializer

import os
import tempfile
from PIL import Image

MOVIE_URL = reverse("cinema:movie-list")


def sample_movie(**params) -> Movie:
    genre, _ = Genre.objects.get_or_create(name="test genre")
    actor, _ = Actor.objects.get_or_create(
        first_name="TestFirst", last_name="TestSecond"
    )
    defaults = {
        "title": "test movie",
        "description": "test description",
        "duration": 60,
    }
    defaults.update(params)
    movie = Movie.objects.create(**defaults)
    movie.genres.add(genre)
    movie.actors.add(actor)
    return movie


class UnauthenticatedMovieViewSetTests(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)
        self.assertEquals(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieViewSetTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@gmail.com", password="testpassword"
        )
        self.client.force_authenticate(self.user)

    def test_movie_list(self):
        sample_movie()
        sample_movie(title="Another movie")

        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all().order_by("title")
        serializer = MovieListSerializer(movies, many=True)
        self.assertEquals(res.status_code, status.HTTP_200_OK)
        self.assertEquals(res.data["results"], serializer.data)

    def test_movie_list_pagination(self):
        for i in range(6):
            sample_movie(title=f"Movie{i}")

        res = self.client.get(MOVIE_URL)

        self.assertEquals(res.status_code, status.HTTP_200_OK)

        self.assertIn("count", res.data)
        self.assertIn("next", res.data)
        self.assertIn("results", res.data)

        self.assertEquals(len(res.data["results"]), 5)
        self.assertEquals(res.data["count"], 6)

    def test_movies_second_page_pagination(self):
        for i in range(6):
            sample_movie(title=f"Movie {i}")

        res = self.client.get(MOVIE_URL, {"page": 2})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 1)
        self.assertIsNotNone(res.data["previous"])

    def test_movie_create(self):
        self.user.is_staff = True
        self.user.save()
        genre = Genre.objects.create(name="Action")
        actor = Actor.objects.create(first_name="Tom", last_name="Hardy")

        payload = {
            "title": "Mad Max",
            "description": "Post-apocalyptic action",
            "duration": 120,
            "genres": [genre.id],
            "actors": [actor.id],
        }
        res = self.client.post(MOVIE_URL, payload)

        self.assertEquals(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(id=res.data["id"])
        self.assertEquals(movie.title, payload["title"])
        self.assertEquals(movie.description, payload["description"])
        self.assertEquals(movie.duration, payload["duration"])

        genres = movie.genres.all()
        self.assertIn(genre, genres)
        self.assertEquals(genres.count(), 1)

    def test_movie_list_filter(self):
        movie_inception = sample_movie(title="Inception")
        movie_genre = sample_movie(title="Drama Movie")
        movie_actor = sample_movie(title="Action Movie")

        genre = Genre.objects.create(name="Drama")
        actor = Actor.objects.create(first_name="Actor", last_name="Filter")

        movie_genre.genres.add(genre)
        movie_actor.actors.add(actor)

        title_res = self.client.get(MOVIE_URL, {"title": "Inception"})

        serializer_title = MovieListSerializer([movie_inception], many=True)
        self.assertEqual(title_res.data["results"], serializer_title.data)

        genre_res = self.client.get(MOVIE_URL, {"genres": f"{genre.id}"})
        serializer_genre = MovieListSerializer([movie_genre], many=True)
        self.assertEqual(genre_res.data["results"], serializer_genre.data)

        actor_res = self.client.get(MOVIE_URL, {"actors": f"{actor.id}"})
        serializer_actor = MovieListSerializer([movie_actor], many=True)
        self.assertEqual(actor_res.data["results"], serializer_actor.data)

        self.assertEqual(title_res.status_code, status.HTTP_200_OK)
        self.assertEqual(genre_res.status_code, status.HTTP_200_OK)
        self.assertEqual(actor_res.status_code, status.HTTP_200_OK)

    def test_movie_list_complex_filter(self):

        genre1 = Genre.objects.create(name="Action")
        genre2 = Genre.objects.create(name="Drama")
        actor1 = Actor.objects.create(first_name="Tom", last_name="Hanks")

        movie1 = sample_movie(title="Forrest Gump")
        movie1.genres.add(genre1)
        movie1.actors.add(actor1)

        movie2 = sample_movie(title="Forrest Road")
        movie2.genres.add(genre2)

        sample_movie(title="Saving Private Ryan")

        res_title = self.client.get(MOVIE_URL, {"title": "forrest"})
        self.assertEqual(len(res_title.data["results"]), 2)

        res_complex = self.client.get(
            MOVIE_URL, {"title": "Forrest", "genres": f"{genre1.id}"}
        )

        self.assertEqual(len(res_complex.data["results"]), 1)
        self.assertEqual(res_complex.data["results"][0]["id"], movie1.id)

        res_ids = self.client.get(MOVIE_URL,
                                  {"genres": f"{genre1.id},{genre2.id}"})

        self.assertEqual(len(res_ids.data["results"]), 2)

    def test_movie_detail_view(self):
        movie = sample_movie()
        url = reverse("cinema:movie-detail", args=[movie.id])
        res = self.client.get(url)
        serializer = MovieDetailSerializer(movie)
        self.assertEquals(res.status_code, status.HTTP_200_OK)
        self.assertEquals(res.data, serializer.data)

    def test_create_movie_with_wrong_data(self):
        self.user.is_staff = True
        self.user.save()
        genre = Genre.objects.create(name="Action")
        actor = Actor.objects.create(first_name="Tom", last_name="Hardy")

        payload = {
            "title": "",
            "description": "Post-apocalyptic action",
            "duration": 120,
            "genres": [genre.id],
            "actors": [actor.id],
            "image": "",
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEquals(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upload_image_to_movie(self):
        self.user.is_staff = True
        self.user.save()
        movie = sample_movie()
        url = reverse("cinema:movie-upload-image", args=[movie.id])

        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10), "white")
            img.save(ntf, format="JPEG")
            ntf.seek(0)

            res = self.client.post(url, {"image": ntf}, format="multipart")

        movie.refresh_from_db()
        self.assertEquals(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)
        self.assertTrue(os.path.exists(movie.image.path))

        movie.image.delete()
