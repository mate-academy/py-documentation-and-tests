import os
import tempfile

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

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
    defaults = {
        "first_name": "George",
        "last_name": "Clooney",
    }
    defaults.update(params)

    return Actor.objects.create(**defaults)


def sample_movie_session(**params):
    cinema_hall = CinemaHall.objects.create(
        name="Blue",
        rows=20,
        seats_in_row=20,
    )

    defaults = {
        "show_time": "2022-06-02 14:00:00",
        "movie": None,
        "cinema_hall": cinema_hall,
    }
    defaults.update(params)

    return MovieSession.objects.create(**defaults)


def image_upload_url(movie_id):
    return reverse("cinema:movie-upload-image", args=[movie_id])


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


class UnauthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required_for_movie_list(self):
        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_auth_required_for_movie_detail(self):
        movie = sample_movie()

        res = self.client.get(detail_url(movie.id))

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_auth_required_for_create_movie(self):
        payload = {
            "title": "Test movie",
            "description": "Test description",
            "duration": 110,
            "genres": [],
            "actors": [],
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user@test.com",
            password="testpass123",
        )
        self.client.force_authenticate(self.user)

    def test_retrieve_movies(self):
        movie1 = sample_movie(title="Movie 1")
        movie2 = sample_movie(title="Movie 2")

        res = self.client.get(MOVIE_URL)

        movies = Movie.objects.prefetch_related("genres", "actors").order_by("title")
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)
        self.assertEqual(len(res.data), 2)
        self.assertEqual(res.data[0]["title"], movie1.title)
        self.assertEqual(res.data[1]["title"], movie2.title)

    def test_movie_detail(self):
        movie = sample_movie()

        genre = sample_genre()
        actor = sample_actor()
        movie.genres.add(genre)
        movie.actors.add(actor)

        res = self.client.get(detail_url(movie.id))
        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_regular_user_cannot_create_movie(self):
        genre = sample_genre()
        actor = sample_actor()

        payload = {
            "title": "Forbidden movie",
            "description": "Forbidden description",
            "duration": 123,
            "genres": [genre.id],
            "actors": [actor.id],
        }

        res = self.client.post(MOVIE_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_filter_movies_by_title(self):
        movie1 = sample_movie(title="Black Widow")
        movie2 = sample_movie(title="Matrix")

        res = self.client.get(MOVIE_URL, {"title": "black"})

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)

        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

    def test_filter_movies_by_genres(self):
        genre1 = sample_genre(name="Action")
        genre2 = sample_genre(name="Drama")
        movie1 = sample_movie(title="Movie 1")
        movie2 = sample_movie(title="Movie 2")

        movie1.genres.add(genre1)
        movie2.genres.add(genre2)

        res = self.client.get(MOVIE_URL, {"genres": f"{genre1.id}"})

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)

        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

    def test_filter_movies_by_multiple_genres(self):
        genre1 = sample_genre(name="Action")
        genre2 = sample_genre(name="Drama")
        movie1 = sample_movie(title="Movie 1")
        movie2 = sample_movie(title="Movie 2")
        movie3 = sample_movie(title="Movie 3")

        movie1.genres.add(genre1)
        movie2.genres.add(genre2)
        movie3.genres.add(genre1, genre2)

        res = self.client.get(
            MOVIE_URL, {"genres": f"{genre1.id},{genre2.id}"}
        )

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie3)

        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertIn(serializer3.data, res.data)

    def test_filter_movies_by_actors(self):
        actor1 = sample_actor(first_name="Keanu", last_name="Reeves")
        actor2 = sample_actor(first_name="Tom", last_name="Cruise")
        movie1 = sample_movie(title="Movie 1")
        movie2 = sample_movie(title="Movie 2")

        movie1.actors.add(actor1)
        movie2.actors.add(actor2)

        res = self.client.get(MOVIE_URL, {"actors": f"{actor1.id}"})

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)

        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

    def test_filter_movies_by_multiple_actors(self):
        actor1 = sample_actor(first_name="Keanu", last_name="Reeves")
        actor2 = sample_actor(first_name="Tom", last_name="Cruise")
        movie1 = sample_movie(title="Movie 1")
        movie2 = sample_movie(title="Movie 2")
        movie3 = sample_movie(title="Movie 3")

        movie1.actors.add(actor1)
        movie2.actors.add(actor2)
        movie3.actors.add(actor1, actor2)

        res = self.client.get(
            MOVIE_URL, {"actors": f"{actor1.id},{actor2.id}"}
        )

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie3)

        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertIn(serializer3.data, res.data)

    def test_movie_list_contains_expected_fields(self):
        sample_movie()

        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("id", res.data[0])
        self.assertIn("title", res.data[0])
        self.assertIn("description", res.data[0])
        self.assertIn("duration", res.data[0])
        self.assertIn("genres", res.data[0])
        self.assertIn("actors", res.data[0])
        self.assertIn("image", res.data[0])

    def test_movie_detail_contains_expected_fields(self):
        movie = sample_movie()
        movie.genres.add(sample_genre())
        movie.actors.add(sample_actor())

        res = self.client.get(detail_url(movie.id))

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("id", res.data)
        self.assertIn("title", res.data)
        self.assertIn("description", res.data)
        self.assertIn("duration", res.data)
        self.assertIn("genres", res.data)
        self.assertIn("actors", res.data)
        self.assertIn("image", res.data)


class AdminMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = get_user_model().objects.create_superuser(
            email="admin@myproject.com",
            password="password",
        )
        self.client.force_authenticate(self.admin)

    def tearDown(self):
        for movie in Movie.objects.all():
            if movie.image:
                movie.image.delete()

    def test_create_movie(self):
        genre1 = sample_genre(name="Action")
        genre2 = sample_genre(name="Drama")
        actor1 = sample_actor(first_name="Tom", last_name="Holland")
        actor2 = sample_actor(first_name="Zendaya", last_name="Coleman")

        payload = {
            "title": "New movie",
            "description": "Interesting movie",
            "duration": 130,
            "genres": [genre1.id, genre2.id],
            "actors": [actor1.id, actor2.id],
        }

        res = self.client.post(MOVIE_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        movie = Movie.objects.get(id=res.data["id"])
        self.assertEqual(movie.title, payload["title"])
        self.assertEqual(movie.description, payload["description"])
        self.assertEqual(movie.duration, payload["duration"])
        self.assertEqual(set(movie.genres.all()), {genre1, genre2})
        self.assertEqual(set(movie.actors.all()), {actor1, actor2})

    def test_create_movie_without_image(self):
        genre = sample_genre()
        actor = sample_actor()

        payload = {
            "title": "Movie without image",
            "description": "Description",
            "duration": 100,
            "genres": [genre.id],
            "actors": [actor.id],
        }

        res = self.client.post(MOVIE_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        movie = Movie.objects.get(id=res.data["id"])
        self.assertFalse(movie.image)

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

    def test_upload_image_bad_request(self):
        movie = sample_movie()
        url = image_upload_url(movie.id)

        res = self.client.post(url, {"image": "not image"}, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_image_to_movie_list_creates_movie_without_image(self):
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
        movie = sample_movie()
        url = image_upload_url(movie.id)

        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")

        res = self.client.get(detail_url(movie.id))

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)

    def test_image_url_is_shown_on_movie_list(self):
        movie = sample_movie()
        url = image_upload_url(movie.id)

        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")

        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data[0].keys())

    def test_image_url_is_shown_on_movie_session_list(self):
        movie = sample_movie()
        sample_movie_session(movie=movie)

        url = image_upload_url(movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")

        res = self.client.get(MOVIE_SESSION_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("movie_image", res.data[0].keys())