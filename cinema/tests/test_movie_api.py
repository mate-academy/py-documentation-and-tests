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


class UnAuthenticatedMovieApiTests(TestCase):
    def setUP(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(MOVIE_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class IsAuthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test_user@email.com",
            "testuserpass"
        )

        self.client.force_authenticate(self.user)

    def test_list_movies(self):
        movie_1 = sample_movie()
        movie_2 = sample_movie()
        genre = sample_genre()
        actor = sample_actor()

        movie_1.genres.add(genre)
        movie_2.genres.add(genre)
        movie_1.actors.add(actor)
        movie_2.actors.add(actor)

        response = self.client.get(MOVIE_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_movies_filtered_by_title(self):
        movie_1 = sample_movie()
        movie_2 = sample_movie(title="Sample movie new")
        genre = sample_genre()
        actor = sample_actor()

        movie_1.genres.add(genre)
        movie_2.genres.add(genre)
        movie_1.actors.add(actor)
        movie_2.actors.add(actor)

        response = self.client.get(MOVIE_URL, {"title": "new"})

        serializer_1 = MovieListSerializer(movie_1)
        serializer_2 = MovieListSerializer(movie_2)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn(serializer_1.data, response.data)
        self.assertIn(serializer_2.data, response.data)

    def test_movies_filtered_by_genres(self):
        movie_1 = sample_movie()
        movie_2 = sample_movie()

        genre_1 = sample_genre()
        genre_2 = sample_genre(name="Horror")
        movie_2.genres.add(genre_1, genre_2)

        response = self.client.get(MOVIE_URL, {"genres": f"{genre_1.id},{genre_2.id}"})

        serializer_1 = MovieListSerializer(movie_1)
        serializer_2 = MovieListSerializer(movie_2)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn(serializer_1.data, response.data)
        self.assertIn(serializer_2.data, response.data)

    def test_movies_filtered_by_actors(self):
        movie_1 = sample_movie()
        movie_2 = sample_movie()

        actor_1 = sample_actor()
        actor_2 = sample_actor(first_name="Will", last_name="Smith")
        movie_2.actors.add(actor_1, actor_2)

        response = self.client.get(MOVIE_URL, {"actors": f"{actor_1.id},{actor_2.id}"})

        serializer_1 = MovieListSerializer(movie_1)
        serializer_2 = MovieListSerializer(movie_2)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn(serializer_1.data, response.data)
        self.assertIn(serializer_2.data, response.data)

    def test_retrieve_movie_detail(self):
        movie = sample_movie()
        genre = sample_genre()
        actor = sample_actor()
        movie.genres.add(genre)
        movie.actors.add(actor)

        url = detail_url(movie.id)
        response = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_creation_forbidden_for_unauthenticated(self):
        data = {
            "title": "Sample movie",
            "description": "Sample description",
            "duration": 90
        }

        response = self.client.post(MOVIE_URL, data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class IsAdminMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test_user@email.com",
            "testuserpass",
            is_staff=True
        )

        self.client.force_authenticate(self.user)

    def test_admin_allowed_create(self):
        data = {
            "title": "Sample movie",
            "description": "Sample description",
            "duration": 90
        }

        response = self.client.post(MOVIE_URL, data)
        movie = Movie.objects.get(id=response.data["id"])

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        for key in data:
            self.assertEqual(data[key], getattr(movie, key))

    def test_create_movie_with_genres_and_actors(self):
        genre_1 = sample_genre()
        genre_2 = sample_genre(name="Horror")
        actor_1 = sample_actor()
        actor_2 = sample_actor(first_name="Will", last_name="Smith")
        data = {
            "title": "Sample movie",
            "description": "Sample description",
            "duration": 90,
            "genres": [genre_1.id, genre_2.id],
            "actors": [actor_1.id, actor_2.id]
        }

        response = self.client.post(MOVIE_URL, data)
        movie = Movie.objects.get(id=response.data["id"])
        genres = movie.genres.all()
        actors = movie.actors.all()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(genres.count(), 2)
        self.assertEqual(actors.count(), 2)
        self.assertIn(genre_1, genres)
        self.assertIn(genre_2, genres)
        self.assertIn(actor_1, actors)
        self.assertIn(actor_2, actors)

    def test_patch_not_allowed(self):
        movie = sample_movie()
        url = detail_url(movie.id)

        response = self.client.patch(url, data={"title": "not allowed"})

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_put_not_allowed(self):
        movie = sample_movie()
        url = detail_url(movie.id)

        response = self.client.put(
            url,
            data={
                "title": "New Sample movie",
                "description": "New Sample description",
                "duration": 100,
            }
        )

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_destroy_not_allowed(self):
        movie = sample_movie()
        url = detail_url(movie.id)

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


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
