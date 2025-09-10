import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APITestCase
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


def movie_detail_url(movie_id: int):
    return reverse("cinema:movie-detail", args=[movie_id])


class MovieImageUploadTests(APITestCase):
    def setUp(self):
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


class UnauthenticatedMovieApiTests(APITestCase):

    def test_unauthenticated_movie(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(APITestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="test@email.com",
            password="test_password",
        )
        self.client.force_authenticate(self.user)
        self.genre_1 = sample_genre()
        self.genre_2 = sample_genre(name="Crime")
        self.actor_1 = sample_actor()
        self.actor_2 = sample_actor(first_name="John")

        self.movie_no_genre_actor = sample_movie()
        self.movie_with_genre = sample_movie(title="genre")
        self.movie_with_genre_2 = sample_movie(title="genre 2")
        self.movie_with_actor_1 = sample_movie(title="actor")
        self.movie_with_actor_2 = sample_movie(title="actor 2")
        self.movie_with_actor_and_genre = sample_movie(title="actors and genres")
        self.movie_with_genre.genres.add(self.genre_1)
        self.movie_with_genre_2.genres.add(self.genre_2)
        self.movie_with_actor_1.actors.add(self.actor_1)
        self.movie_with_actor_2.actors.add(self.actor_2)
        self.movie_with_actor_and_genre.genres.add(self.genre_2)
        self.movie_with_actor_and_genre.actors.add(self.actor_1)

    def test_movie_list(self):

        movie = Movie.objects.all()
        serializer = MovieListSerializer(movie, many=True)

        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.data, serializer.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_filter_movies_by_genres(self):
        res = self.client.get(
            MOVIE_URL,
            {"genres": f"{self.genre_1.id},{self.genre_2.id}"}
        )

        serializer_without_genres = MovieListSerializer(self.movie_no_genre_actor)
        serializer_genre_1 = MovieListSerializer(self.movie_with_genre)
        serializer_genre_2 = MovieListSerializer(self.movie_with_actor_and_genre)

        self.assertIn(serializer_genre_1.data, res.data),
        self.assertIn(serializer_genre_2.data, res.data),
        self.assertNotIn(serializer_without_genres.data, res.data),
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_filter_movies_by_actors(self):
        res = self.client.get(
            MOVIE_URL,
            {"actors": f"{self.actor_1.id},{self.actor_2.id}"}
        )

        serializer_without_actors = MovieListSerializer(self.movie_no_genre_actor)
        serializer_actor_1 = MovieListSerializer(self.movie_with_actor_1)
        serializer_actor_2 = MovieListSerializer(self.movie_with_actor_2)

        self.assertIn(serializer_actor_1.data, res.data),
        self.assertIn(serializer_actor_2.data, res.data),
        self.assertNotIn(serializer_without_actors.data, res.data),
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_filter_movies_by_title(self):

        res = self.client.get(
            MOVIE_URL,
            {"title": "act"}
        )

        serializer_with_sample_title = MovieListSerializer(self.movie_no_genre_actor)
        serializer_actor = MovieListSerializer(self.movie_with_actor_1)
        serializer_actor_2 = MovieListSerializer(self.movie_with_actor_2)

        self.assertIn(serializer_actor.data, res.data),
        self.assertIn(serializer_actor_2.data, res.data),
        self.assertNotIn(serializer_with_sample_title.data, res.data),
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_filter_by_combined_params(self):
        res = self.client.get(
            MOVIE_URL,
            {
                "title": "act",
                "genres": f"{self.genre_2.id}",
                "actors": f"{self.actor_1.id}",
            }
        )

        serializer_with_genre_2 = MovieListSerializer(self.movie_with_genre_2)
        serializer_with_actor_1 = MovieListSerializer(self.movie_with_actor_1)
        serializer_with_title_act = MovieListSerializer(self.movie_with_actor_2)
        serializer_right = MovieListSerializer(self.movie_with_actor_and_genre)

        self.assertIn(serializer_right.data, res.data),
        self.assertNotIn(serializer_with_genre_2.data, res.data),
        self.assertNotIn(serializer_with_actor_1.data, res.data),
        self.assertNotIn(serializer_with_title_act.data, res.data),
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_retrieve_movie_detail(self):
        movie_url = movie_detail_url(self.movie_with_actor_and_genre.id)

        res = self.client.get(movie_url)
        serializer = MovieDetailSerializer(self.movie_with_actor_and_genre)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "not admin test",
            "description": "effort to create movie in unauthorized way",
            "duration": 10
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

class AdminMovieAPITest(APITestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="admin@test.email",
            password="admin_test_password",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        payload = {
            "title": "admins dream",
            "description": "What admin thinks in free time?",
            "duration": 120
        }

        res = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(id=res.data["id"])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_create_movie_with_actor(self):
        actor = sample_actor(first_name="Earl", last_name="Grey")
        actor_2 = sample_actor(first_name="Lapsang", last_name="Souchong")
        actor_3 =sample_actor(first_name="Long", last_name="Jing")
        genre = sample_genre(name="Black Tea")
        genre_2 = sample_genre(name="Green Tea")

        payload = {
            "title": "Tea Ceremony",
            "description": "Mistery of tea",
            "duration": 200,
            "actors": [actor.id, actor_2.id, actor_3.id],
            "genres": [genre.id, genre_2.id]
        }

        res = self.client.post(MOVIE_URL, payload)

        movie = Movie.objects.get(id=res.data["id"])
        actors = movie.actors.all()
        genres = movie.genres.all()
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn(actor, actors)
        self.assertIn(actor_2, actors)
        self.assertIn(actor_3, actors)
        self.assertIn(genre, genres)
        self.assertIn(genre_2, genres)
        self.assertEqual(genres.count(), 2)
        self.assertEqual(actors.count(), 3)

    def test_delete_movie_not_allowed(self):
        movie = sample_movie()

        url = movie_detail_url(movie.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
