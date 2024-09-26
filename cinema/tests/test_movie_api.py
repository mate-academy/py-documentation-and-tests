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


class UnauthenticatedMovieApiTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(MOVIE_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create(
            email="new_user@test.com",
            password="new password"
        )
        self.client.force_authenticate(self.user)

    def test_movies_list(self):
        sample_movie()
        movie_with_actors_and_genres = sample_movie()

        actor1 = sample_actor()
        actor2 = sample_actor(first_name="First", last_name="Last")

        genre1 = Genre.objects.create(name="Horror")
        genre2 = sample_genre()

        movie_with_actors_and_genres.genres.add(genre1, genre2)
        movie_with_actors_and_genres.actors.add(actor1, actor2)

        response = self.client.get(MOVIE_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_movies_filter_by_title(self):
        title = "New movie"
        movie_with_title = sample_movie(title=title)
        movie_with_extended_title = sample_movie(title=title + " smth adding")
        movie_without_title = sample_movie()

        response = self.client.get(MOVIE_URL, {"title": title})

        serializer_with_title = MovieListSerializer(movie_with_title)
        serializer_with_extended_title = MovieListSerializer(
            movie_with_extended_title
        )
        serializer_without_title = MovieListSerializer(movie_without_title)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertIn(serializer_with_title.data, response.data)
        self.assertIn(serializer_with_extended_title.data, response.data)
        self.assertNotIn(serializer_without_title.data, response.data)

    def test_movies_filter_by_actors(self):
        movie_with_actor1 = sample_movie()
        movie_with_actors = sample_movie()
        movie_without_actor = sample_movie()

        actor1 = sample_actor()
        actor2 = sample_actor(first_name="First", last_name="Last")

        movie_with_actor1.actors.add(actor1)
        movie_with_actors.actors.add(actor1, actor2)

        response = self.client.get(
            MOVIE_URL,
            {
                "actors": f"{actor1.id},{actor2.id}"
            }
        )

        serializer_with_actor1 = MovieListSerializer(movie_with_actor1)
        serializer_with_actors = MovieListSerializer(movie_with_actors)
        serializer_without_actor = MovieListSerializer(movie_without_actor)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertIn(serializer_with_actor1.data, response.data)
        self.assertIn(serializer_with_actors.data, response.data)
        self.assertNotIn(serializer_without_actor.data, response.data)

    def test_movies_filter_by_genres(self):
        movie_with_genre1 = sample_movie()
        movie_with_genres = sample_movie()
        movie_without_genre = sample_movie()

        genre1 = sample_genre(name="Horror")
        genre2 = sample_genre(name="Detective")

        movie_with_genre1.genres.add(genre1)
        movie_with_genres.genres.add(genre2, genre1)

        response = self.client.get(
            MOVIE_URL,
            {
                "genres": f"{genre1.id},{genre2.id}"
            }
        )

        serializer_with_genre1 = MovieListSerializer(movie_with_genre1)
        serializer_with_genres = MovieListSerializer(movie_with_genres)
        serializer_without_genre = MovieListSerializer(movie_without_genre)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertIn(serializer_with_genre1.data, response.data)
        self.assertIn(serializer_with_genres.data, response.data)
        self.assertNotIn(serializer_without_genre.data, response.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        movie.actors.add(sample_actor())
        movie.genres.add(sample_genre())

        response = self.client.get(detail_url(movie.id))

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_forbidden_create(self):
        payload = {
            "title": "Simple",
            "description": "Forbidden",
            "duration": 55
        }

        response = self.client.post(MOVIE_URL, data=payload)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTest(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            email="admin@admin.com",
            password="adm1n_%Q"
        )
        self.client.force_authenticate(self.user)

    def test_movie_create(self):
        payload = {
            "title": "Transformers 100",
            "description": "100 seria of transformers only on Netflix",
            "duration": 310
        }

        response = self.client.post(MOVIE_URL, data=payload)

        movie = Movie.objects.get(pk=response.data["id"])

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        for variable_name in payload:
            self.assertEqual(
                payload[variable_name],
                getattr(movie, variable_name)
            )

    def test_movie_create_with_actors_and_genres(self):
        actor1 = sample_actor()
        actor2 = sample_actor(last_name="New")

        genre1 = sample_genre()
        genre2 = sample_genre(name="Horror")

        payload = {
            "title": "Transformers 100",
            "description": "100 seria of transformers only on Netflix",
            "duration": 310,
            "genres": [genre2.id, genre1.id],
            "actors": [actor1.id, actor2.id],
        }

        response = self.client.post(MOVIE_URL, data=payload)

        movie = Movie.objects.get(pk=response.data["id"])

        genres = movie.genres.all()
        actors = movie.actors.all()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertIn(genre1, genres)
        self.assertIn(genre2, genres)
        self.assertEqual(genres.count(), 2)

        self.assertIn(actor1, actors)
        self.assertIn(actor2, actors)
        self.assertEqual(actors.count(), 2)

    def test_update_method_not_allowed(self):
        payload = {
            "title": "Not allowed update",
            "description": "Check for updating not allowed",
            "duration": 405,
        }
        movie = sample_movie()

        response = self.client.put(detail_url(movie.id), data=payload)

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def test_delete_method_not_allowed(self):
        movie = sample_movie(title="Deletion")

        response = self.client.delete(detail_url(movie.id))

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED
        )
