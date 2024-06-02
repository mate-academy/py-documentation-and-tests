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


class UnauthenticatedMovieListApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(MOVIE_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieListApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@test.com", "Password123!"
        )
        self.client.force_authenticate(self.user)

    def test_movie_list(self):
        sample_movie()
        sample_movie()
        sample_movie()
        movie_filtered_with_actors_genres_title = sample_movie()

        actor_1 = Actor.objects.create(
            first_name="Actor 1 first name",
            last_name="Actor 1 last name",
        )
        actor_2 = Actor.objects.create(
            first_name="Actor 2 first name",
            last_name="Actor 2 last name",
        )
        movie_filtered_with_actors_genres_title.actors.add(actor_1, actor_2)

        genre_1 = Genre.objects.create(name="Genre 1")
        genre_2 = Genre.objects.create(name="Genre 2")
        movie_filtered_with_actors_genres_title.genres.add(genre_1, genre_2)

        title = "Test movie"
        movie_filtered_with_actors_genres_title.title = title
        movie_filtered_with_actors_genres_title.save()

        res = self.client.get(MOVIE_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.data, serializer.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 4)

    def test_filter_movies_by_actors(self):
        movie_without_actors = sample_movie()
        movie_filtered_with_actors = sample_movie()

        actor_1 = Actor.objects.create(
            first_name="Actor 1 first name",
            last_name="Actor 1 last name",
        )
        actor_2 = Actor.objects.create(
            first_name="Actor 2 first name",
            last_name="Actor 2 last name",
        )
        movie_filtered_with_actors.actors.add(actor_1, actor_2)

        res = self.client.get(
            MOVIE_URL, {"actors": f"{actor_1.id},{actor_2.id}"}
        )

        serializer_movie_without_actors = MovieListSerializer(
            movie_without_actors
        )
        serializer_movie_filtered_with_actors = MovieListSerializer(
            movie_filtered_with_actors
        )

        self.assertEqual(
            res.data, [serializer_movie_filtered_with_actors.data]
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertNotIn(serializer_movie_without_actors.data, res.data)

    def test_filter_movies_by_genres(self):
        movie_without_genres = sample_movie()
        movie_filtered_with_genres = sample_movie()

        genre_1 = Genre.objects.create(name="Genre 1")
        genre_2 = Genre.objects.create(name="Genre 2")
        movie_filtered_with_genres.genres.add(genre_1, genre_2)

        res = self.client.get(
            MOVIE_URL, {"genres": f"{genre_1.id},{genre_2.id}"}
        )

        serializer_movie_without_genres = MovieListSerializer(
            movie_without_genres
        )
        serializer_movie_filtered_with_genres = MovieListSerializer(
            movie_filtered_with_genres
        )

        self.assertEqual(
            res.data, [serializer_movie_filtered_with_genres.data]
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertNotIn(serializer_movie_without_genres.data, res.data)

    def test_movie_list_filter_by_title(self):
        movie_1 = sample_movie(title="Movie 11")
        movie_2 = sample_movie(title="Movie 12")
        movie_3 = sample_movie(title="Movie 23")

        res = self.client.get(MOVIE_URL, {"title": "Movie 1"})

        serializer_movie_1 = MovieListSerializer(movie_1)
        serializer_movie_2 = MovieListSerializer(movie_2)
        serializer_movie_3 = MovieListSerializer(movie_3)

        expected_data = [serializer_movie_1.data, serializer_movie_2.data]
        expected_data_sorted = sorted(expected_data, key=lambda x: x["title"])
        res_data_sorted = sorted(res.data, key=lambda x: x["title"])

        self.assertEqual(res_data_sorted, expected_data_sorted)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertNotIn(serializer_movie_3.data, res.data)

    def test_retrieve_movie(self):
        movie = sample_movie()
        res = self.client.get(MOVIE_URL + f"{movie.id}/")

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.data, serializer.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_create_movie_forbidden(self):
        res = self.client.post(MOVIE_URL, {"fake_key": "fake_value"})

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminBusTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admintest@test1.com", "Password123!@", is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_movie_with_actors_genres(self):
        genre = Genre.objects.create(name="Genre 1")
        actor = Actor.objects.create(
            first_name="Actor 1 first name",
            last_name="Actor 1 last name",
        )
        payload = {
            "title": "stringsda",
            "description": "stringdsasda",
            "duration": 111,
            "genres": [genre.id],
            "actors": [actor.id],
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        movie = Movie.objects.get(id=res.data["id"])
        self.assertEqual(movie.title, payload["title"])
        self.assertEqual(movie.description, payload["description"])
        self.assertEqual(movie.duration, payload["duration"])
        self.assertEqual(genre.id, payload["genres"][0])
        self.assertEqual(actor.id, payload["actors"][0])

        self.assertEqual(len(movie.genres.all()), 1)
        self.assertEqual(len(movie.actors.all()), 1)

    def test_delete_movie_not_allowed(self):
        movie = sample_movie()
        res = self.client.delete(MOVIE_URL + f"{movie.id}/")

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
