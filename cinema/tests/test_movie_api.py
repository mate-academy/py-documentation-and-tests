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


class UnauthenticatedMovieApiTests(TestCase):

    def SetUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(MOVIE_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.genre_action = sample_genre(name="action")
        self.genre_fantastic = sample_genre(name="fantastic")

        self.actor_schwarzenegger = sample_actor(
            first_name="Arnold",
            last_name="Schwarzenegger"
        )
        self.actor_stallone = sample_actor(
            first_name="Sylvester ",
            last_name="Stallone"
        )

        self.secondary_actor = sample_actor()

        self.movie_terminator = sample_movie(title="Terminator")
        self.movie_terminator.genres.add(
            self.genre_action,
            self.genre_fantastic
        )
        self.movie_terminator.actors.add(
            self.actor_schwarzenegger,
            self.secondary_actor
        )

        self.movie_rambo = sample_movie(title="Rambo")
        self.movie_rambo.genres.add(
            self.genre_action
        )
        self.movie_rambo.actors.add(
            self.actor_stallone,
            self.secondary_actor
        )

        self.user = get_user_model().objects.create_user(
            "vasyl@pryhodko.com",
            "vasyl123456",
        )

        self.movies = Movie.objects.all()

        self.client = (APIClient())
        self.client.force_authenticate(self.user)

    def test_list_movies(self):
        response = self.client.get(MOVIE_URL)
        serializer = MovieListSerializer(self.movies, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_search_movie_by_genre(self):
        serializer = MovieListSerializer(self.movies, many=True)
        query_params = {"genres": ""}
        response = self.client.get(MOVIE_URL, query_params)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

        query_params["genres"] = (
            f"{self.genre_fantastic.id},"
            f"{self.genre_action.id}"
        )
        response = self.client.get(MOVIE_URL, query_params)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)
        query_params["genres"] = (
            f"{self.genre_fantastic.id}"
        )

        serializer = MovieListSerializer(self.movies.filter(
            genres__in=[self.genre_fantastic.id]
            ),
            many=True
        )
        response = self.client.get(MOVIE_URL, query_params)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(serializer.data, response.data)

    def test_search_movie_by_actors(self):
        serializer = MovieListSerializer(self.movies, many=True)
        query_params = {"actors": ""}
        response = self.client.get(MOVIE_URL, query_params)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

        query_params["actors"] = (
            f"{self.actor_schwarzenegger.id},"
            f"{self.actor_stallone.id}"
        )
        response = self.client.get(MOVIE_URL, query_params)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)
        query_params["actors"] = (
            f"{self.actor_schwarzenegger.id}"
        )

        serializer = MovieListSerializer(self.movies.filter(
            actors__in=[self.actor_schwarzenegger.id]
            ),
            many=True
        )
        response = self.client.get(MOVIE_URL, query_params)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(serializer.data, response.data)

    def test_search_movie_by_title(self):
        serializer = MovieListSerializer(self.movies, many=True)
        query_params = {"title": ""}
        response = self.client.get(MOVIE_URL, query_params)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

        serializer = MovieListSerializer(self.movies.filter(
            title__icontains="terminator"
            ),
            many=True
        )
        query_params["title"] = "terminator"
        response = self.client.get(MOVIE_URL, query_params)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

        query_params["title"] = "kindergarden_cop"
        response = self.client.get(MOVIE_URL, query_params)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_get_movie_detail(self):
        response = self.client.get(detail_url(self.movie_terminator.id))
        serializer = MovieDetailSerializer(self.movie_terminator)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(serializer.data, response.data)

    def test_create_movie_forbidden(self):
        payload = {
            "title": "terminator 2",
            "description": "cool movie",
            "duration": 90,
            "genres": [self.genre_fantastic.id, self.genre_action.id],
            "actors": [self.actor_schwarzenegger.id, self.secondary_actor.id],
            "image": ""
        }
        response = self.client.post(MOVIE_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminMovieApiTests(TestCase):
    def setUp(self):
        self.genre_action = sample_genre(name="action")
        self.genre_fantastic = sample_genre(name="fantastic")

        self.actor_schwarzenegger = sample_actor(
            first_name="Arnold",
            last_name="Schwarzenegger"
        )
        self.actor_stallone = sample_actor(
            first_name="Sylvester ",
            last_name="Stallone"
        )

        self.secondary_actor = sample_actor()

        self.movie_terminator = sample_movie(title="Terminator")
        self.movie_terminator.genres.add(
            self.genre_action,
            self.genre_fantastic
        )
        self.movie_terminator.actors.add(
            self.actor_schwarzenegger,
            self.secondary_actor
        )

        self.movie_rambo = sample_movie(title="Rambo")
        self.movie_rambo.genres.add(
            self.genre_action
        )
        self.movie_rambo.actors.add(
            self.actor_stallone,
            self.secondary_actor
        )

        self.user = get_user_model().objects.create_superuser(
            "vasyl@pryhodko.com",
            "vasyl123456",
        )

        self.movies = Movie.objects.all()

        self.client = (APIClient())
        self.client.force_authenticate(self.user)

    def test_create_movie(self):
        payload = {
            "title": "terminator 2",
            "description": "cool movie",
            "duration": 90,
            "genres": [self.genre_fantastic.id, self.genre_action.id],
            "actors": [self.actor_schwarzenegger.id, self.secondary_actor.id],
            "image": ""
        }
        response = self.client.post(MOVIE_URL, payload)
        movie = Movie.objects.get(id=response.data["id"])
        genres = movie.genres.all()
        actors = movie.actors.all()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(actors.count(), 2)
        self.assertEqual(genres.count(), 2)

        self.assertIn(self.genre_action, genres)
        self.assertIn(self.genre_fantastic, genres)

        self.assertIn(self.actor_schwarzenegger, actors)
        self.assertIn(self.secondary_actor, actors)
