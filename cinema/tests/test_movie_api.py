import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor

from cinema.serializers import (
    MovieListSerializer,
    MovieDetailSerializer,
    MovieImageSerializer,
    MovieSerializer,
)
from cinema.views import MovieViewSet

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


class UnauthenticatedCinemaAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required_movie(self):
        res = self.client.get(MOVIE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedCinemaAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com", password="test_password"
        )
        self.client.force_authenticate(self.user)

    def test_movies_list(self):
        movie = sample_movie()
        actor = sample_actor(first_name="Robert", last_name="Downey Jr.")
        genre = sample_genre(name="Action")

        movie.genres.add(genre)
        movie.actors.add(actor)

        res = self.client.get(MOVIE_URL)
        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_title(self):
        movie1 = sample_movie(title="The Avengers")
        movie2 = sample_movie(title="Avengers: Endgame")
        movie3 = sample_movie(title="Iron Man")

        res = self.client.get(MOVIE_URL, {"title": "avengers"})

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)
        serializer3 = MovieListSerializer(movie3)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_filter_movies_by_genres(self):
        genre1 = sample_genre(name="Sci-Fi")
        genre2 = sample_genre(name="Adventure")
        movie1 = sample_movie(title="Star Wars")
        movie2 = sample_movie(title="Indiana Jones")
        movie1.genres.add(genre1)
        movie2.genres.add(genre2)

        res = self.client.get(MOVIE_URL, {"genres": f"{genre1.id}"})

        serializer1 = MovieListSerializer(movie1)
        serializer2 = MovieListSerializer(movie2)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

    def test_filter_movies_by_actors(self):
        movie_1 = sample_movie(title="John Wick")
        movie_2 = sample_movie(title="The Matrix")

        actor_1 = sample_actor(first_name="Keanu", last_name="Reeves")
        actor_2 = sample_actor(first_name="Laurence", last_name="Fishburne")

        movie_1.actors.add(actor_1)
        movie_2.actors.add(actor_2)

        res = self.client.get(MOVIE_URL, {"actors": actor_1.id})

        serializer1 = MovieListSerializer(movie_1)
        serializer2 = MovieListSerializer(movie_2)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

    def test_get_serializer_class(self):
        view = MovieViewSet()
        view.action = "list"
        self.assertEqual(view.get_serializer_class(), MovieListSerializer)
        view.action = "retrieve"
        self.assertEqual(view.get_serializer_class(), MovieDetailSerializer)
        view.action = "upload_image"
        self.assertEqual(view.get_serializer_class(), MovieImageSerializer)
        view.action = "create"
        self.assertEqual(view.get_serializer_class(), MovieSerializer)

    def test_retrieve_movie_detail(self):
        genre1 = sample_genre(name="Thriller")
        genre2 = sample_genre(name="Mystery")
        genre3 = sample_genre(name="Horror")

        actor1 = sample_actor(first_name="Tom", last_name="Cruise")
        actor2 = sample_actor(first_name="Nicole", last_name="Kidman")
        actor3 = sample_actor(first_name="Simon", last_name="Peg")

        movie = sample_movie(title="Eyes Wide Shut", description="A psychological thriller", duration=159)
        movie.genres.set([genre1, genre2, genre3])
        movie.actors.set([actor1, actor2, actor3])

        url = detail_url(movie.id)
        res = self.client.get(url)

        serializer = MovieDetailSerializer(instance=movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "Interstellar",
            "description": "A journey through space and time",
            "duration": 169,
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminCinemaAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@test.com", password="test_password", is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        payload = {
            "title": "Blade Runner",
            "description": "A dystopian future",
            "duration": 117,
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        movie = Movie.objects.get(id=res.data["id"])

        for key in payload:
            self.assertEqual(payload[key], getattr(movie, key))

    def test_create_movie_with_actors(self):
        actor1 = Actor.objects.create(first_name="Harrison", last_name="Ford")
        actor2 = Actor.objects.create(first_name="Rutger", last_name="Hauer")
        actor3 = Actor.objects.create(first_name="Sean", last_name="Young")
        payload = {
            "title": "Blade Runner",
            "description": "A dystopian future",
            "duration": 117,
            "actors": [actor1.id, actor2.id, actor3.id],
        }

        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        movie = Movie.objects.get(pk=res.data["id"])
        actors = movie.actors.all()
        self.assertIn(actor1, actors)
        self.assertIn(actor2, actors)
        self.assertIn(actor3, actors)
        self.assertEqual(actors.count(), 3)

    def test_create_movie_with_genres(self):
        genre1 = Genre.objects.create(name="Action")
        genre2 = Genre.objects.create(name="Sci-Fi")
        genre3 = Genre.objects.create(name="Adventure")

        payload = {
            "title": "Guardians of the Galaxy",
            "description": "A group of intergalactic criminals must pull together to stop a fanatical warrior.",
            "duration": 121,
            "genres": [genre1.id, genre2.id, genre3.id],
        }
        res = self.client.post(MOVIE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        movie = Movie.objects.get(pk=res.data["id"])
        genres = movie.genres.all()
        self.assertIn(genre1, genres)
        self.assertIn(genre2, genres)
        self.assertIn(genre3, genres)
        self.assertEqual(genres.count(), 3)

    def test_delete_movie_not_allowed(self):
        movie = sample_movie()
        url = detail_url(movie.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
